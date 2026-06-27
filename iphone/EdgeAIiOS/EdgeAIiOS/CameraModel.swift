import AVFoundation
import SwiftUI

final class CameraModel: NSObject, ObservableObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    @Published var label: String = "…"
    @Published var confidence: Float = 0
    @Published var latencyMs: Double = 0
    @Published var fps: Double = 0

    let session = AVCaptureSession()
    private let classifier = FrameClassifier()
    private let videoQueue = DispatchQueue(label: "camera.video.queue")

    private var busy = false
    private var lastStamp = CFAbsoluteTimeGetCurrent()

    func start() {
        if !classifier.isReady {
            label = "модель не найдена — соберите .mlpackage (см. README)"
        }
        requestAccessThenConfigure()
    }

    func stop() {
        if session.isRunning { session.stopRunning() }
    }

    private func requestAccessThenConfigure() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            configure()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                if granted { self?.configure() }
            }
        default:
            DispatchQueue.main.async { self.label = "доступ к камере запрещён" }
        }
    }

    private func configure() {
        session.beginConfiguration()
        session.sessionPreset = .vga640x480

        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
              let input = try? AVCaptureDeviceInput(device: device),
              session.canAddInput(input) else {
            session.commitConfiguration()
            DispatchQueue.main.async { self.label = "нет камеры" }
            return
        }
        session.addInput(input)

        let output = AVCaptureVideoDataOutput()
        output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA]
        output.alwaysDiscardsLateVideoFrames = true
        output.setSampleBufferDelegate(self, queue: videoQueue)
        if session.canAddOutput(output) { session.addOutput(output) }

        session.commitConfiguration()
        videoQueue.async { self.session.startRunning() }
    }

    // Буферы задней камеры повёрнуты как landscape-right относительно портретного UI;
    // .right даёт Vision вертикальное изображение, когда телефон держат в портрете.
    private var visionOrientation: CGImagePropertyOrientation { .right }

    // MARK: - AVCaptureVideoDataOutputSampleBufferDelegate

    func captureOutput(_ output: AVCaptureOutput,
                       didOutput sampleBuffer: CMSampleBuffer,
                       from connection: AVCaptureConnection) {
        // Без модели не крутим инференс вхолостую — оставляем живое превью и подсказку в оверлее.
        guard classifier.isReady, !busy,
              let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        busy = true

        classifier.classify(pixelBuffer, orientation: visionOrientation) { [weak self] result in
            guard let self = self else { return }
            let now = CFAbsoluteTimeGetCurrent()
            let instFps = 1.0 / max(now - self.lastStamp, 1e-3)
            self.lastStamp = now
            DispatchQueue.main.async {
                if let r = result {
                    self.label = r.label
                    self.confidence = r.confidence
                    self.latencyMs = r.latencyMs
                }
                self.fps = self.fps == 0 ? instFps : 0.8 * self.fps + 0.2 * instFps
            }
            self.busy = false
        }
    }
}

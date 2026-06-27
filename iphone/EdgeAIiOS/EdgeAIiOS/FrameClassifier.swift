import CoreML
import Vision
import CoreVideo

struct ClassificationResult {
    let label: String
    let confidence: Float
    let latencyMs: Double
}

final class FrameClassifier {
    private let vnModel: VNCoreMLModel?
    /// false, если модель ещё не добавлена в бандл (приложение не падает, а показывает подсказку).
    let isReady: Bool

    init() {
        guard let url = Bundle.main.url(forResource: "MobileNetV3Small", withExtension: "mlmodelc") else {
            print("[FrameClassifier] MobileNetV3Small.mlmodelc не найден в бандле. " +
                  "Соберите Model/export_coreml.py и добавьте .mlpackage в таргет — см. README.")
            self.vnModel = nil
            self.isReady = false
            return
        }
        var model: VNCoreMLModel?
        do {
            let config = MLModelConfiguration()
            config.computeUnits = .all   // CPU + GPU + Neural Engine
            let mlModel = try MLModel(contentsOf: url, configuration: config)
            model = try VNCoreMLModel(for: mlModel)
        } catch {
            print("[FrameClassifier] Не удалось загрузить Core ML-модель: \(error)")
        }
        self.vnModel = model
        self.isReady = (model != nil)
    }

    /// Классифицировать один кадр. `orientation` должна соответствовать повороту буфера камеры.
    func classify(_ pixelBuffer: CVPixelBuffer,
                  orientation: CGImagePropertyOrientation,
                  completion: @escaping (ClassificationResult?) -> Void) {
        guard let vnModel = vnModel else { completion(nil); return }
        let start = CFAbsoluteTimeGetCurrent()
        let request = VNCoreMLRequest(model: vnModel) { request, _ in
            let elapsedMs = (CFAbsoluteTimeGetCurrent() - start) * 1000.0
            guard let top = (request.results as? [VNClassificationObservation])?.first else {
                completion(nil)
                return
            }
            let label = top.identifier.components(separatedBy: ",").first ?? top.identifier
            completion(ClassificationResult(label: label, confidence: top.confidence, latencyMs: elapsedMs))
        }
        request.imageCropAndScaleOption = .centerCrop

        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: orientation, options: [:])
        do {
            try handler.perform([request])
        } catch {
            completion(nil)
        }
    }
}

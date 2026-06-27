import SwiftUI

struct ContentView: View {
    @StateObject private var camera = CameraModel()

    var body: some View {
        ZStack(alignment: .topLeading) {
            CameraPreview(session: camera.session)
                .ignoresSafeArea()

            VStack(alignment: .leading, spacing: 6) {
                Text(camera.label)
                    .font(.system(size: 28, weight: .bold))
                    .foregroundColor(.green)
                Text(String(format: "уверенность %.0f%%", camera.confidence * 100))
                    .foregroundColor(.white)
                Text(String(format: "инференс %.1f мс  |  %.1f FPS", camera.latencyMs, camera.fps))
                    .foregroundColor(.yellow)
            }
            .padding(10)
            .background(.black.opacity(0.45))
            .cornerRadius(10)
            .padding(16)
        }
        .onAppear { camera.start() }
        .onDisappear { camera.stop() }
    }
}

#Preview {
    ContentView()
}

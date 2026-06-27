import SwiftUI

struct ContentView: View {
    @StateObject private var camera = CameraModel()

    var body: some View {
        ZStack(alignment: .top) {
            CameraPreview(session: camera.session)
                .ignoresSafeArea()

            VStack(alignment: .leading, spacing: 6) {
                Text(camera.label)
                    .font(.system(size: 26, weight: .bold))
                    .foregroundColor(.green)
                Text(String(format: "уверенность %.0f%%", camera.confidence * 100))
                    .foregroundColor(.white)
                Text(String(format: "инференс %.1f мс  |  %.1f FPS", camera.latencyMs, camera.fps))
                    .foregroundColor(.yellow)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(10)
            .background(.black.opacity(0.45))
            .cornerRadius(10)
            .padding(.horizontal, 16)
            .padding(.top, 8)
        }
        .onAppear { camera.start() }
        .onDisappear { camera.stop() }
    }
}

#Preview {
    ContentView()
}

import Foundation
import AppKit
import Vision
import PDFKit

func recognize(_ image: CGImage) throws -> String {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["fr-FR", "en-US"]
    request.usesLanguageCorrection = true
    try VNImageRequestHandler(cgImage: image).perform([request])
    return (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
}

do {
    let url = URL(fileURLWithPath: CommandLine.arguments[1])
    if url.pathExtension.lowercased() == "pdf" {
        guard let document = PDFDocument(url: url), document.pageCount <= 50 else {
            throw NSError(domain: "NOVA", code: 1, userInfo: [NSLocalizedDescriptionKey: "PDF illisible ou plus de 50 pages OCR."])
        }
        for index in 0..<document.pageCount {
            guard let page = document.page(at: index) else { continue }
            let thumbnail = page.thumbnail(of: NSSize(width: 1800, height: 2400), for: .mediaBox)
            guard let image = thumbnail.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
            print("[page \(index + 1) · OCR]\n\(try recognize(image))")
        }
    } else {
        guard let image = NSImage(contentsOf: url)?.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
            throw NSError(domain: "NOVA", code: 2, userInfo: [NSLocalizedDescriptionKey: "Image illisible."])
        }
        print(try recognize(image))
    }
} catch {
    FileHandle.standardError.write(Data(error.localizedDescription.utf8))
    exit(1)
}

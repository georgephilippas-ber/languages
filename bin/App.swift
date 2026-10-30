import Cocoa

final class AppDelegate: NSObject, NSApplicationDelegate {
    var worker: Process?
    var stopping = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        let menu = NSMenu()
        let item = NSMenuItem()
        menu.addItem(item)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Open Languages", action: #selector(openBrowser), keyEquivalent: "o")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit Languages", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        item.submenu = appMenu
        NSApp.mainMenu = menu
        let root = ProcessInfo.processInfo.environment["LANGUAGES_DATA"].map {
            NSString(string: $0).expandingTildeInPath
        } ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("tmp/languages").path
        do {
            try FileManager.default.createDirectory(atPath: root, withIntermediateDirectories: true)
            let logURL = URL(fileURLWithPath: root).appendingPathComponent("Languages.log")
            if !FileManager.default.fileExists(atPath: logURL.path) {
                FileManager.default.createFile(atPath: logURL.path, contents: nil)
            }
            let log = try FileHandle(forWritingTo: logURL)
            log.seekToEndOfFile()
            let process = Process()
            process.executableURL = Bundle.main.resourceURL!.appendingPathComponent("runtime/languages/languages")
            process.standardOutput = log
            process.standardError = log
            process.terminationHandler = { [weak self] child in
                DispatchQueue.main.async {
                    guard let self = self, !self.stopping else { return }
                    if child.terminationStatus != 0 {
                        let alert = NSAlert()
                        alert.messageText = "Languages could not start"
                        alert.informativeText = "See \(logURL.path) for details. Port 8100 may already be in use."
                        alert.runModal()
                    }
                    NSApp.terminate(nil)
                }
            }
            worker = process
            try process.run()
        } catch {
            let alert = NSAlert()
            alert.messageText = "Languages could not start"
            alert.informativeText = error.localizedDescription
            alert.runModal()
            NSApp.terminate(nil)
        }
    }

    @objc func openBrowser() {
        if ProcessInfo.processInfo.environment["LANGUAGES_NO_BROWSER"] == "1" { return }
        let url = URL(string: "http://127.0.0.1:8100")!
        if let firefox = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "org.mozilla.firefox") {
            let configuration = NSWorkspace.OpenConfiguration()
            configuration.createsNewApplicationInstance = false
            NSWorkspace.shared.open([url], withApplicationAt: firefox, configuration: configuration)
        } else {
            NSWorkspace.shared.open(url)
        }
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        openBrowser()
        return true
    }

    func applicationWillTerminate(_ notification: Notification) {
        stopping = true
        if let worker = worker, worker.isRunning {
            worker.terminate()
            worker.waitUntilExit()
        }
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()

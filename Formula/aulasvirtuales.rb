class Aulasvirtuales < Formula
  desc "Toolkit to interact with UTN FRBA's Moodle virtual classrooms"
  homepage "https://github.com/alexFiorenza/aulasvirtuales-toolkit"
  url "https://github.com/alexFiorenza/aulasvirtuales-toolkit/archive/refs/tags/aulasvirtuales-cli-v0.2.0.tar.gz"
  sha256 "e754a60b01b3eee75bc518129c3ecd51dc67adb13f82d313942d01f5f4be8104"
  version "0.2.0"

  depends_on "python@3.12"

  def install
    # Create an isolated Python virtual environment
    system "python3", "-m", "venv", libexec
    
    # We navigate to the extracted repo and install the base library and CLI manually
    system libexec/"bin/pip", "install", "./packages/aulasvirtuales"
    system libexec/"bin/pip", "install", "./packages/aulasvirtuales-cli"
    
    # Isolate Playwright browsers inside the formula's share directory to prevent ~/.cache pollution.
    # Placing it in `share` instead of `libexec` prevents Homebrew's linkage checker from crashing 
    # on pre-compiled Chromium binaries which have small headers.
    ENV["PLAYWRIGHT_BROWSERS_PATH"] = share/"playwright-browsers"
    system libexec/"bin/playwright", "install", "chromium"
    
    # Create a wrapper executable that injects the PLAYWRIGHT_BROWSERS_PATH environment variable at runtime
    (bin/"aulasvirtuales").write_env_script libexec/"bin/aulasvirtuales", 
      PLAYWRIGHT_BROWSERS_PATH: share/"playwright-browsers"
  end

  test do
    system "#{bin}/aulasvirtuales", "--help"
  end
end

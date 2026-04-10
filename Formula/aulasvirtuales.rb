class Aulasvirtuales < Formula
  desc "Toolkit to interact with UTN FRBA's Moodle virtual classrooms"
  homepage "https://github.com/alexFiorenza/aulasvirtuales-toolkit"
  url "https://github.com/alexFiorenza/aulasvirtuales-toolkit/archive/refs/tags/packages/aulasvirtuales-cli-v0.1.0.tar.gz"
  sha256 "DUMMY_SHA256"
  version "0.1.0"

  depends_on "python@3.12"

  def install
    # Create an isolated Python virtual environment
    system "python3", "-m", "venv", libexec
    
    # We navigate to the extracted repo and install the base library and CLI manually
    system libexec/"bin/pip", "install", "./packages/aulasvirtuales"
    system libexec/"bin/pip", "install", "./packages/aulasvirtuales-cli"
    
    # Isolate Playwright browsers inside the formula's libexec directory to prevent ~/.cache pollution
    ENV["PLAYWRIGHT_BROWSERS_PATH"] = libexec/"playwright-browsers"
    system libexec/"bin/playwright", "install", "chromium"
    
    # Create a wrapper executable that injects the PLAYWRIGHT_BROWSERS_PATH environment variable at runtime
    (bin/"aulasvirtuales").write_env_script libexec/"bin/aulasvirtuales", 
      PLAYWRIGHT_BROWSERS_PATH: libexec/"playwright-browsers"
  end

  test do
    system "#{bin}/aulasvirtuales", "--help"
  end
end

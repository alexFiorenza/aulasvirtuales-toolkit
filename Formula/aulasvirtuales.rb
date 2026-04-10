class Aulasvirtuales < Formula
  desc "Toolkit to interact with UTN FRBA's Moodle virtual classrooms"
  homepage "https://github.com/alexFiorenza/aulasvirtuales-toolkit"
  url "https://github.com/alexFiorenza/aulasvirtuales-toolkit/archive/refs/tags/aulasvirtuales-cli-v0.3.0.tar.gz"
  sha256 "b3f3abedbe496dfa43b112c049029dac027428fc8477b7a173d620c526e677ec"
  version "0.3.0"

  depends_on "python@3.12"

  # Prevent Homebrew from relocating pre-compiled Chromium dylibs whose headers
  # are too small for the rewritten install names.
  skip_clean "share/playwright-browsers"

  def install
    # Create an isolated Python virtual environment
    system "python3", "-m", "venv", libexec
    
    # We navigate to the extracted repo and install the base library and CLI manually
    system libexec/"bin/pip", "install", "./packages/core"
    system libexec/"bin/pip", "install", "./apps/aulasvirtuales-cli"
    
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

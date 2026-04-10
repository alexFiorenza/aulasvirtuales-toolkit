class Aulasvirtuales < Formula
  desc "Toolkit to interact with UTN FRBA's Moodle virtual classrooms"
  homepage "https://github.com/alexFiorenza/aulasvirtuales-toolkit"
  url "https://github.com/alexFiorenza/aulasvirtuales-toolkit/archive/refs/tags/aulasvirtuales-cli-v0.3.0.tar.gz"
  sha256 "b3f3abedbe496dfa43b112c049029dac027428fc8477b7a173d620c526e677ec"
  version "0.3.0"

  depends_on "python@3.12"

  def install
    # Create an isolated Python virtual environment
    system "python3", "-m", "venv", libexec

    # Copy source packages into the prefix so post_install can pip-install them.
    # pip install must happen in post_install to avoid Homebrew's dylib relocation
    # phase, which fails on native extensions (orjson, playwright) whose Mach-O
    # headers are too small for the rewritten install names.
    (libexec/"src").install "packages", "apps"

    # Create a wrapper executable that injects the PLAYWRIGHT_BROWSERS_PATH environment variable at runtime.
    (bin/"aulasvirtuales").write_env_script libexec/"bin/aulasvirtuales",
      PLAYWRIGHT_BROWSERS_PATH: share/"playwright-browsers"
  end

  def post_install
    system libexec/"bin/pip", "install", "#{libexec}/src/packages/core[ocr]"
    system libexec/"bin/pip", "install", "#{libexec}/src/apps/aulasvirtuales-cli"
    rm_rf libexec/"src"

    ENV["PLAYWRIGHT_BROWSERS_PATH"] = share/"playwright-browsers"
    system libexec/"bin/playwright", "install", "chromium"
  end

  test do
    system "#{bin}/aulasvirtuales", "--help"
  end
end

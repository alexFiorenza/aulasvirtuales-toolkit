class Aulasvirtuales < Formula
  desc "Toolkit to interact with UTN FRBA's Moodle virtual classrooms"
  homepage "https://github.com/alexFiorenza/aulasvirtuales-toolkit"
  url "https://github.com/alexFiorenza/aulasvirtuales-toolkit/archive/refs/tags/aulasvirtuales-cli-v0.5.0.tar.gz"
  sha256 "aefcb4ab35d6b2acb6c41801e2bdd6e33b6f165ce33a03e856486d2424fab6f4"
  version "0.5.0"

  depends_on "python@3.12"

  def install
    system "python3", "-m", "venv", libexec

    (libexec/"src").install "packages", "apps"

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

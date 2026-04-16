class Aulasvirtuales < Formula
  desc "Toolkit to interact with UTN FRBA's Moodle virtual classrooms"
  homepage "https://github.com/alexFiorenza/aulasvirtuales-toolkit"
  url "https://github.com/alexFiorenza/aulasvirtuales-toolkit/archive/refs/tags/aulasvirtuales-cli-v0.6.2.tar.gz"
  sha256 "1de9b0db374c07b7d2ed918e5b9aa273fc172ab1200a8c1df19bef66222d615a"
  version "0.6.2"

  depends_on "python@3.12"

  def install
    system "python3", "-m", "venv", libexec

    (libexec/"src").install "packages", "apps"

    (bin/"aulasvirtuales").write_env_script libexec/"bin/aulasvirtuales",
      PLAYWRIGHT_BROWSERS_PATH: share/"playwright-browsers"
  end

  def post_install
    system libexec/"bin/pip", "install", "#{libexec}/src/packages/core[ocr,docx,markdown]"
    system libexec/"bin/pip", "install", "#{libexec}/src/apps/aulasvirtuales-cli"
    rm_rf libexec/"src"

    ENV["PLAYWRIGHT_BROWSERS_PATH"] = share/"playwright-browsers"
    system libexec/"bin/playwright", "install", "chromium"
  end

  test do
    system "#{bin}/aulasvirtuales", "--help"
  end
end

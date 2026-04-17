class Aulasvirtuales < Formula
  desc "Toolkit to interact with UTN FRBA's Moodle virtual classrooms"
  homepage "https://github.com/alexFiorenza/aulasvirtuales-toolkit"
  url "https://github.com/alexFiorenza/aulasvirtuales-toolkit/archive/refs/tags/aulasvirtuales-cli-v0.7.0.tar.gz"
  sha256 "f225191faeeef7520ded18c1a1d50c39cb55035cecda9f2645264ed910d965df"
  version "0.7.0"

  depends_on "python@3.12"

  def install
    system "python3", "-m", "venv", libexec

    (libexec/"src").install "packages", "apps"

    (bin/"aulasvirtuales").write_env_script libexec/"bin/aulasvirtuales",
      PLAYWRIGHT_BROWSERS_PATH: share/"playwright-browsers"
  end

  def post_install
    system libexec/"bin/pip", "install", "#{libexec}/src/packages/core[full]"
    system libexec/"bin/pip", "install", "#{libexec}/src/apps/aulasvirtuales-cli"
    rm_rf libexec/"src"

    ENV["PLAYWRIGHT_BROWSERS_PATH"] = share/"playwright-browsers"
    system libexec/"bin/playwright", "install", "chromium"
  end

  test do
    system "#{bin}/aulasvirtuales", "--help"
  end
end

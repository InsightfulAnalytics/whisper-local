# Homebrew formula TEMPLATE for Whisper Local (macOS / Linux via a personal tap).
#
# Whisper Local has a large, ML-heavy dependency tree (ctranslate2, faster-whisper,
# sherpa-onnx, …) that isn't practical to vendor as Homebrew "resource" stanzas,
# so this formula installs the published PyPI package into an isolated virtualenv.
# That keeps it off the user's system Python while staying maintainable.
#
# This is NOT homebrew-core material (core forbids pip-from-network installs);
# it's meant for a personal tap: `brew tap drajb/tap && brew install whisper-local`.
# See docs/distribution.md for how to set up the tap.
#
# Replace after a release exists:
#   <VERSION>      e.g. 0.10.0
#   <SDIST_SHA256> sha256 of the source tarball from PyPI (or the GitHub sdist)

class WhisperLocal < Formula
  include Language::Python::Virtualenv

  desc "Free, offline AI dictation — press a hotkey, speak, get text at the cursor"
  homepage "https://github.com/drajb/whisper-local"
  url "https://files.pythonhosted.org/packages/source/w/whisper-local/whisper_local-<VERSION>.tar.gz"
  sha256 "<SDIST_SHA256>"
  license "MIT"

  depends_on "python@3.12"

  # Installs whisper-local and pulls its dependencies into the venv at install
  # time. (Resource pinning is intentionally omitted — see the header note.)
  def install
    virtualenv_create(libexec, "python3.12")
    system libexec/"bin/pip", "install", "whisper-local==#{version}"
    bin.install_symlink libexec/"bin/whisper-local"
    bin.install_symlink libexec/"bin/wl"
  end

  test do
    assert_match "whisper-local", shell_output("#{bin}/whisper-local --version")
  end
end

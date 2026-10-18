# Get a portable Windows EXE (no Python required on the laptop)

This source ZIP does not contain a Windows EXE. Build it once using GitHub Actions:

1. Sign in to GitHub and create a new **private** repository.
2. Upload the contents of the CitrusDrop folder, including `.github/workflows/windows-portable.yml` (GitHub's web upload may hide dot-folders; check that the workflow is present).
3. Open the **Actions** tab, select **Build portable Windows app**, and click **Run workflow**.
4. When the run finishes, download the **CitrusDrop-Windows-Portable** artifact.
5. Unzip the downloaded artifact, then unzip `CitrusDrop-Windows-Portable.zip` inside it.
6. Double-click `CitrusDrop.exe`. Python is not required.

Windows SmartScreen may warn about an unsigned new application. Only run builds you trust. FFmpeg is still required separately for video features. The EXE is built for x64 Windows 10/11 by GitHub's Windows runner.

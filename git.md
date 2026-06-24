git branch -M main
git remote add origin "https://github.com/bader913/rayyan-lite-cashier.git"
git push -u origin main


Set-ExecutionPolicy -Scope Process Bypass -Force

powershell -ExecutionPolicy Bypass -File .\apply_rayyan_lite_theme_backup_dark.ps1 `
  -TargetRoot "C:\Users\Bader\OneDrive\Desktop\trial"
修正提交 `baab55e` 已推回 #1669。原分支的回歸測試先紅後綠；格式檢查通過，混音 100、播放 188、介面 383 項通過。引擎 446 項通過、1 項 Windows 影片重新連結失敗（#1536）。含 Windows 相依修正的整合版重新編譯後，引擎 447、混音 100、播放 188、介面 383，共 1,118 項通過、5 項依設定略過。四個 crate 的 all-targets Clippy（`-D warnings`）通過。GitHub 的 CI、Nix、SonarCloud 三項均為 `action_required`。

[舊版失敗紀錄](chorus-continue-1674/regression-before.log) · [原分支測試](chorus-continue-1674/regression-pr.log) · [整合版測試](chorus-continue-1674/regression-windows.log) · [整合版 Clippy](chorus-continue-1674/clippy-windows.log)

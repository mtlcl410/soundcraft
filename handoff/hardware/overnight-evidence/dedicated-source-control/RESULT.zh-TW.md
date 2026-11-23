# 同時收發 Clock 與 MTC 的硬體長測

實測 96 秒。Clock 收到 4603/4608；MTC quarter-frame 收到 11515/11520，piece 次序跳號 0 次，跟隨失鎖計數 0。

按第一次 Clock 的實體收發時間配對，起點相差 6 個輸入 pulse。扣除首尾各一秒邊界後，每個視窗使用 2253 個 pulse。首段中位相位 +3.785 ms，末段 +1.343 ms，兩窗差 -2.442 ms。輸入空檔、失鎖或邊界計數差會改變序號映射。此處列出的相位差僅供追查，不能當作累積時鐘漂移。 程序 private bytes 的前後視窗中位數差 -153600 bytes。

各段最大 F8 間隔為送碼工具 21.383 ms、第一段 DIN 收件 21.473 ms、轉送後輸入 21.516 ms、實體 Clock 輸出 24.576 ms。各自的最大值可能來自不同 pulse；JSON 另列送端最長八個空檔在相同 ordinal 的三段對照。送端若超過 150 ms，該段不符合連續穩速輸入假設。

[逐項數值](window-analysis.json) · [裝置與程式狀態](result.json) · [環境檢查](environment-result.json)

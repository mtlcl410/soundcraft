# 同時收發 Clock 與 MTC 的硬體長測

實測 64 秒。Clock 收到 3067/3072；MTC quarter-frame 收到 7675/7680，piece 次序跳號 0 次，跟隨失鎖計數 0。

按第一次 Clock 的實體收發時間配對，起點相差 1059 個輸入 pulse。扣除首尾各一秒邊界後，每個視窗使用 1485 個 pulse。首段中位相位 +1.371 ms，末段 -0.132 ms，兩窗差 -1.503 ms。程序 private bytes 的前後視窗中位數差 +446464 bytes。完整計數保留起停邊界；捨去邊界只用於比較穩定段相位。

各段最大 F8 間隔為送碼工具 21.415 ms、第一段 DIN 收件 21.471 ms、轉送後輸入 21.512 ms、實體 Clock 輸出 23.285 ms。各自的最大值可能來自不同 pulse；JSON 另列送端最長八個空檔在相同 ordinal 的三段對照。送端若超過 150 ms，該段不符合連續穩速輸入假設。

[逐項數值](window-analysis.json) · [裝置與程式狀態](result.json) · [環境檢查](environment-result.json)

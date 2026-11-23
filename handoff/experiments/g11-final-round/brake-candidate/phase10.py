from pathlib import Path
p=Path('../brake-candidate/crates/playback/src/clock_follow.rs');s=p.read_text().replace('else {self.short.period_us()}','''else {
            let recent=(self.wire_stamps[12]-self.wire_stamps[8]) as f64/4.;
            if self.steady.period_us().is_some_and(|period| (recent-period).abs()>0.05*period) {Some(recent)} else {self.short.period_us()}
        }''');p.write_text(s)

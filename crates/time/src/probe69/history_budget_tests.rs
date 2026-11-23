use super::history::History;
use soundcraft_time::{Range,SampleRate,TempoMap};

fn historical_grid() -> TempoMap {
    let mut grid = TempoMap::default();
    for n in 0..1250 {
        grid.set_tempo(n * 960, 100. + (n % 13) as f64).unwrap();
    }
    grid
}

#[test]
fn nonzero_continue_keeps_its_sample_without_pinning_the_prior_hours() {
    let sr = SampleRate::HZ_48000;
    let mut grid = historical_grid();
    let before = grid.clone();
    let anchor = 990 * 960 + 321;
    History::default().compact(&mut grid,sr,anchor,vec![]);
    assert!(grid.tempos().len() <= 512, "{} events retained at nonzero SPP",grid.tempos().len());
    for tick in [anchor-31,anchor,anchor+93,1101*960,1800*960] {
        assert_eq!(grid.tick_to_samples(tick,sr),before.tick_to_samples(tick,sr));
    }
}

#[test]
fn completed_early_takes_do_not_increase_the_unreferenced_budget() {
    let sr = SampleRate::HZ_48000;
    let mut grid = historical_grid();
    // Each old take needs three complete tempo intervals from its own recording.
    let take_ticks: Vec<_> = (1..=20).map(|i| (i*30*960+100,(i*30+2)*960+200)).collect();
    let spans: Vec<_> = take_ticks.iter().map(|&(a,b)| Range::new(grid.tick_to_samples(a,sr),grid.tick_to_samples(b,sr))).collect();
    let mut history = History::default();
    history.compact(&mut grid,sr,0,spans.clone());
    for i in 1250..2050 {
        grid.set_tempo(i*960,100.+(i%13) as f64).unwrap();
        if history.should_compact(&grid) { history.compact(&mut grid,sr,0,spans.clone()); }
        let protected = grid.tempos().iter().filter(|e| take_ticks.iter().any(|&(a,b)| {
            let start = a / 960 * 960;
            (start..=b).contains(&e.tick)
        })).count();
        let unused = grid.tempos().len() - protected;
        assert!(unused <= 512,"{unused} unreferenced events plus {protected} take events");
    }
}

from pathlib import Path
d=Path('E:/soundcraft/compatibility-audit/g11-large-tempo'); w=d/'work'
p=w/'crates/playback/src/sync_input.rs';s=p.read_text().replace('self.step_intervals(previous, noise_us, 2, 0.30, 0.03).or_else(|| self.step_intervals(previous, noise_us, 4, 0.08, 0.4))','self.step_intervals(previous, 2, 0.30, noise_us * 8., 0.03).or_else(|| self.step_intervals(previous, 4, 0.08, noise_us * 2., 0.4))').replace('previous: f64, noise_us: f64, count: usize, threshold: f64, tolerance: f64','previous: f64, count: usize, bpm_fraction: f64, noise_floor: f64, tolerance: f64').replace('if change.abs() < (previous * threshold).max(if count == 2 { 8. } else { 2. } * noise_us) {','// BPM is reciprocal period. Allow for the microsecond rounding of the endpoints.\n        if period <= 0. || change.abs() + 1. / count as f64 < period * bpm_fraction || change.abs() < noise_floor {')
s=s.replace('1. / count as f64 <','1. / (count as f64) <')
s=s.replace('    #[test]\n    fn driver_time_retains','''    #[test]
    fn eight_percent_bpm_steps_in_either_direction_qualify() {
        for (bpm, qualifies) in [(108., true), (92., true), (107., false), (93., false)] {
            let mut fit = PulseFit::<12>::default();
            for pulse in 0..=4 {
                fit.push(pulse, (pulse as f64 * 2_500_000. / bpm).round() as i64);
            }
            assert_eq!(fit.confirmed_step_start(25_000., 0.).is_some(), qualifies, "{bpm}");
        }
    }

    #[test]
    fn driver_time_retains''')
p.write_text(s)
p=w/'crates/ui-egui/src/app/clock_follow/tests/large_steps.rs';s=p.read_text().replace('use super::*;\nfn edges','use super::*;\n\nfn edges').replace('fn edges(pcm: &[f32], start: i64)','fn edges(pcm: &[f32])').replace('start + i as i64','i as i64').replace('edges(&pcm, 0)','edges(&pcm)').replace('            for pulse in 0..=transition + 192 {','            // Feed only the current F8. Render to the next arrival before publishing its grid.\n            // The 30 ms guard represents audio that a grid edit can no longer rewrite.\n            for pulse in 0..=transition + 192 {')
p.write_text(s)
p=w/'crates/ui-egui/src/app/clock_follow/tests/sampler_song.rs';p.write_text(p.read_text().replace('use std::sync::Arc;\npub','use std::sync::Arc;\n\n/// An eighth-note pattern playing a known 96-sample burst at its native pitch.\npub'))
p=w/'crates/mix/src/click.rs';s=p.read_text()+'''
#[cfg(test)]
mod tests {
    use crate::MixEngine;
    use soundcraft_model::Session;
    use soundcraft_time::SampleRate;

    #[test]
    fn clock_limit_defers_a_click_and_plays_its_tail_once() {
        let mut song=Session {sample_rate: SampleRate::HZ_48000,..Default::default()};
        song.edit.click=true;
        let beat = song.tempo.tick_to_samples(soundcraft_time::TICKS_PER_QUARTER,song.sample_rate);
        let mut reference=MixEngine::new(48000.,2048);
        reference.metronome=true;
        let mut expected=vec![vec![0.;2048];2];
        reference.render(&song,beat,2048,&mut expected);
        assert!(expected[0].iter().any(|x|x.abs()>0.01));
        let mut mix=MixEngine::new(48000.,128);
        mix.metronome=true;
        let mut block=vec![vec![0.;128];2];
        let mut pcm=Vec::new();
        for i in 0..20 {
            let limit=soundcraft_time::TICKS_PER_QUARTER - i64::from(i < 3);
            mix.render_with_clock_limit(&song,beat + i*128,128,&mut block,Some(limit));
            pcm.extend_from_slice(&block[0]);
        }
        assert!(pcm[..384].iter().all(|x| *x == 0.));
        assert_eq!(&pcm[384..384+2048],&expected[0]);
    }
}
'''
p.write_text(s)


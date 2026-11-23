fn percentile95(window: &[u32; 32], count: usize) -> u32 {
    let samples = &window[..count];
    if samples.len() < 20 {
        return samples.iter().copied().max().unwrap_or(0);
    }
    let mut largest = 0;
    let mut second = 0;
    for &value in samples {
        second = second.max(largest.min(value));
        largest = largest.max(value);
    }
    second
}


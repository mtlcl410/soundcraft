#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn invalid_failure_index_preserves_the_error_and_existing_cleanup() {
        let (tx, _rx) = mpsc::sync_channel(2);
        let (_done, completions) = mpsc::channel();
        let failure = Completion { packets: Vec::new(), failure: Some((1, "delivery failed".into())) };
        let mut port = PortIo { tx, completions, staged: Vec::new(), pending: 1, rejected: Some(failure) };
        let mut cleanup = VecDeque::from([vec![0xfc]]);
        assert_eq!(port.ready(&mut cleanup), Err("delivery failed".into()));
        assert_eq!(cleanup, VecDeque::from([vec![0xfc]]));
    }
}

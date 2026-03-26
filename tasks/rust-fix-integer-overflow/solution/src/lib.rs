/// Adds two scores together, saturating at 255 on overflow.
pub fn add_scores(a: u8, b: u8) -> u8 {
    a.saturating_add(b)
}

/// Returns the maximum of two scores.
pub fn max_score(a: u8, b: u8) -> u8 {
    if a > b { a } else { b }
}

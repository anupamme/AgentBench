use rust_fix_integer_overflow::{add_scores, max_score};

#[test]
fn test_add_scores_normal() {
    assert_eq!(add_scores(100, 50), 150);
}

#[test]
fn test_add_scores_overflow() {
    assert_eq!(add_scores(200, 100), 255);
}

#[test]
fn test_max_score() {
    assert_eq!(max_score(10, 20), 20);
    assert_eq!(max_score(30, 5), 30);
}

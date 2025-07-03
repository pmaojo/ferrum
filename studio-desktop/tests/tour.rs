use studio_desktop::ui::viewer::TourState;

#[test]
fn tour_state_advances_steps() {
    let mut tour = TourState::default();
    let first = tour.index();
    assert_eq!(first, 0);
    tour.advance();
    assert_eq!(tour.index(), 1);
    // advance through remaining steps
    tour.advance();
    tour.advance();
    // once past the end, index equals number of steps
    let end = tour.index();
    assert_eq!(end, 3);
}

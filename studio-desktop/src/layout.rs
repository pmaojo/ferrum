use bevy::prelude::Vec2;
use std::collections::HashMap;

/// Helper struct implementing simple graph layout algorithms.
pub struct LayoutEngine;

impl LayoutEngine {
    /// Place nodes around a circle with the given radius.
    pub fn circular_layout(names: &[String], radius: f32) -> HashMap<String, Vec2> {
        let n = names.len().max(1) as f32;
        let mut map = HashMap::with_capacity(names.len());
        for (i, name) in names.iter().enumerate() {
            let angle = i as f32 * std::f32::consts::TAU / n;
            map.insert(
                name.clone(),
                Vec2::new(angle.cos() * radius, angle.sin() * radius),
            );
        }
        map
    }

    /// Very basic force-directed layout placeholder.
    /// Currently delegates to `circular_layout` with a fixed radius.
    pub fn force_directed(names: &[String]) -> HashMap<String, Vec2> {
        Self::circular_layout(names, 100.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn circular_layout_deterministic() {
        let names = vec!["A".to_string(), "B".to_string(), "C".to_string()];
        let first = LayoutEngine::circular_layout(&names, 50.0);
        let second = LayoutEngine::circular_layout(&names, 50.0);
        assert_eq!(first, second);
    }

    #[test]
    fn circular_layout_expected_positions() {
        let names = vec!["A".to_string(), "B".to_string(), "C".to_string()];
        let radius = 1.0;
        let layout = LayoutEngine::circular_layout(&names, radius);

        let angles = [
            0.0,
            2.0 * std::f32::consts::PI / 3.0,
            4.0 * std::f32::consts::PI / 3.0,
        ];
        let expected: Vec<Vec2> = angles
            .iter()
            .map(|a| Vec2::new(a.cos() * radius, a.sin() * radius))
            .collect();

        assert!((layout["A"].distance(expected[0])) < 1e-6);
        assert!((layout["B"].distance(expected[1])) < 1e-6);
        assert!((layout["C"].distance(expected[2])) < 1e-6);
    }
}

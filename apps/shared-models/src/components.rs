use serde::{Deserialize, Serialize};
use typeshare::typeshare;

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SharedComponent {
    pub name: String,
    #[serde(default)]
    pub props: Vec<crate::Field>,
}

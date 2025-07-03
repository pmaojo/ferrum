use bevy::prelude::*;
use bevy::tasks::{AsyncComputeTaskPool, Task};

#[derive(Resource, Default)]
pub struct AsyncRuntime;

impl AsyncRuntime {
    pub fn spawn<F, T>(&self, future: F) -> Task<T>
    where
        F: std::future::Future<Output = T> + Send + 'static,
        T: Send + 'static,
    {
        AsyncComputeTaskPool::get().spawn(future)
    }
}

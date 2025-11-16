use anyhow::Result;

pub fn deploy(provider: super::DeployProvider) -> Result<()> {
    use std::process::Command;

    super::build(None)?;

    let status = match provider {
        super::DeployProvider::Fly => Command::new("flyctl").arg("deploy").status()?,
        super::DeployProvider::Railway => Command::new("railway").arg("up").status()?,
        super::DeployProvider::Render => Command::new("render").args(["services", "deploy"]).status()?,
    };

    if !status.success() {
        anyhow::bail!("Deployment failed");
    }

    println!("✅ Deployment finished");
    Ok(())
}


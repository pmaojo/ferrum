use anyhow::Result;
use std::fs;

use ferrum_shared_models::FerrumDsl;

use crate::ownership::{line_hole, write_generated};
use crate::ProjectPaths;

pub fn generate_auth(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    if dsl.app.auth.is_none() {
        return Ok(());
    }
    fs::create_dir_all(&paths.backend)?;
    fs::create_dir_all(paths.frontend.join("components"))?;
    fs::create_dir_all(paths.frontend.join("hooks"))?;

    // The fixed-credential check is a placeholder inside a hole: the real
    // credential check is hand-written and survives recompiles.
    let login_hole = line_hole(
        "    ",
        "auth-login",
        "auth_login",
        "auth:login",
        "if creds.email == \"user@example.com\" && creds.password == \"password\" {\n    Ok(\"token123\".to_string())\n} else {\n    Err(\"invalid_credentials\")\n}",
    );
    let backend_content = "// Authentication handlers\n\n".to_string()
        + "pub struct Credentials {\n    pub email: String,\n    pub password: String,\n}\n\n"
        + "/// Check credentials and return a session token.\n"
        + "pub fn login(creds: Credentials) -> Result<String, &'static str> {\n"
        + &login_hole
        + "}\n";
    write_generated(paths.backend.join("auth.rs"), &backend_content)?;

    let hook_content = "export function useLogin() {\n  return async (email: string, password: string) => {\n    const res = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });\n    return res.json();\n  };\n}\n";
    write_generated(paths.frontend.join("hooks/useLogin.ts"), hook_content)?;

    let form_content = "import React, { useState } from 'react';\nimport { useLogin } from '../hooks/useLogin';\n\nexport function LoginForm() {\n  const login = useLogin();\n  const [email, setEmail] = useState('');\n  const [password, setPassword] = useState('');\n  return (<form onSubmit={e => {e.preventDefault(); login(email, password);}}><input value={email} onChange={e=>setEmail(e.target.value)} placeholder='email'/><input type='password' value={password} onChange={e=>setPassword(e.target.value)} placeholder='password'/><button type='submit'>Login</button></form>);\n}\n";
    write_generated(paths.frontend.join("components/LoginForm.tsx"), form_content)?;
    Ok(())
}

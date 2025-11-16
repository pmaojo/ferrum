use anyhow::Result;
use std::fs;

use ferrum_shared_models::FerrumDsl;

use crate::ProjectPaths;

pub fn generate_auth(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    if dsl.app.auth.is_none() {
        return Ok(());
    }
    fs::create_dir_all(&paths.backend)?;
    fs::create_dir_all(&paths.frontend.join("components"))?;
    fs::create_dir_all(&paths.frontend.join("hooks"))?;

    let backend_content = "// Authentication handlers\n\n".to_string()
        + "pub struct Credentials {\n    pub email: String,\n    pub password: String,\n}\n\n"
        + "/// Very basic credential check returning a fixed token.\n"
        + "pub fn login(creds: Credentials) -> Result<String, &'static str> {\n"
        + "    if creds.email == \"user@example.com\" && creds.password == \"password\" {\n"
        + "        Ok(\"token123\".to_string())\n"
        + "    } else {\n"
        + "        Err(\"invalid_credentials\")\n"
        + "    }\n"
        + "}\n";
    fs::write(paths.backend.join("auth.rs"), backend_content)?;

    let hook_content = "export function useLogin() {\n  return async (email: string, password: string) => {\n    const res = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });\n    return res.json();\n  };\n}\n";
    fs::write(paths.frontend.join("hooks/useLogin.ts"), hook_content)?;

    let form_content = "import React, { useState } from 'react';\nimport { useLogin } from '../hooks/useLogin';\n\nexport function LoginForm() {\n  const login = useLogin();\n  const [email, setEmail] = useState('');\n  const [password, setPassword] = useState('');\n  return (<form onSubmit={e => {e.preventDefault(); login(email, password);}}><input value={email} onChange={e=>setEmail(e.target.value)} placeholder='email'/><input type='password' value={password} onChange={e=>setPassword(e.target.value)} placeholder='password'/><button type='submit'>Login</button></form>);\n}\n";
    fs::write(paths.frontend.join("components/LoginForm.tsx"), form_content)?;
    Ok(())
}

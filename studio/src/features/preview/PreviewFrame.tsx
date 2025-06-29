import { useState } from "react";

/** Live preview of the generated frontend via iframe */
export function PreviewFrame() {
  const [loggedIn, setLoggedIn] = useState(false);
  return (
    <div className="space-y-2">
      <label className="block">
        <input
          type="checkbox"
          className="mr-2"
          checked={loggedIn}
          onChange={(e) => setLoggedIn(e.target.checked)}
        />
        Mock logged in
      </label>
      <iframe
        src="http://localhost:5173"
        className="w-full h-[70vh] border"
      />
    </div>
  );
}

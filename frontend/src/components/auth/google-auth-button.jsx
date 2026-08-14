import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

const GOOGLE_SCRIPT_ID = "google-identity-services";
const GOOGLE_SCRIPT_URL = "https://accounts.google.com/gsi/client";

export function GoogleAuthButton({ disabled = false, onCredential, onError }) {
  const buttonRef = useRef(null);
  const credentialHandlerRef = useRef(onCredential);
  const errorHandlerRef = useRef(onError);
  const [scriptFailed, setScriptFailed] = useState(false);
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim();

  useEffect(() => {
    credentialHandlerRef.current = onCredential;
    errorHandlerRef.current = onError;
  }, [onCredential, onError]);

  useEffect(() => {
    if (!clientId) return undefined;

    let cancelled = false;

    const renderGoogleButton = () => {
      if (cancelled || !buttonRef.current || !window.google?.accounts?.id) return;

      buttonRef.current.innerHTML = "";
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response) => {
          if (response?.credential) {
            credentialHandlerRef.current?.(response.credential);
          } else {
            errorHandlerRef.current?.("Google did not return a credential.");
          }
        },
        ux_mode: "popup",
      });
      window.google.accounts.id.renderButton(buttonRef.current, {
        type: "standard",
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "pill",
        logo_alignment: "left",
        width: Math.min(buttonRef.current.clientWidth || 360, 360),
      });
    };

    if (window.google?.accounts?.id) {
      renderGoogleButton();
      return () => {
        cancelled = true;
      };
    }

    let script = document.getElementById(GOOGLE_SCRIPT_ID);
    if (!script) {
      script = document.createElement("script");
      script.id = GOOGLE_SCRIPT_ID;
      script.src = GOOGLE_SCRIPT_URL;
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }

    const handleLoad = () => {
      setScriptFailed(false);
      renderGoogleButton();
    };
    const handleError = () => {
      setScriptFailed(true);
      errorHandlerRef.current?.("Could not load Google sign-in.");
    };

    script.addEventListener("load", handleLoad);
    script.addEventListener("error", handleError);

    return () => {
      cancelled = true;
      script.removeEventListener("load", handleLoad);
      script.removeEventListener("error", handleError);
    };
  }, [clientId]);

  if (!clientId) {
    return (
      <div>
        <Button type="button" variant="outline" className="w-full" disabled>
          Google sign-in is not configured
        </Button>
        <p className="mt-2 text-center text-xs text-slate-500">
          Add VITE_GOOGLE_CLIENT_ID to the frontend environment.
        </p>
      </div>
    );
  }

  if (scriptFailed) {
    return (
      <Button type="button" variant="outline" className="w-full" disabled>
        Google sign-in is unavailable
      </Button>
    );
  }

  return (
    <div className={disabled ? "pointer-events-none opacity-60" : undefined}>
      <div ref={buttonRef} className="flex min-h-10 w-full justify-center" />
      {disabled ? <p className="mt-2 text-center text-xs text-slate-500">Signing in with Google...</p> : null}
    </div>
  );
}

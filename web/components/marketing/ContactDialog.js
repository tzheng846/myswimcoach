"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogTrigger,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { WEB3FORMS_ACCESS_KEY, CONTACT_EMAIL } from "@/lib/site";

// One reusable "Request a quote" CTA. Every marketing surface mounts this; the trigger
// Button's look is controlled via props. On submit it POSTs to Web3Forms, which emails
// the lead to the inbox configured for WEB3FORMS_ACCESS_KEY.
export default function ContactDialog({
  label = "Request a quote",
  variant = "default",
  size = "default",
  className,
}) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | submitting | success | error
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const payload = {
      access_key: WEB3FORMS_ACCESS_KEY,
      subject: "Swimnetics — quote request",
      from_name: "Swimnetics website",
      name: fd.get("name"),
      email: fd.get("email"),
      message: fd.get("message"),
    };
    setStatus("submitting");
    setError(null);
    try {
      const res = await fetch("https://api.web3forms.com/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (json.success) {
        setStatus("success");
      } else {
        setStatus("error");
        setError(json.message || "Something went wrong. Please try again.");
      }
    } catch {
      setStatus("error");
      setError(`Network error — please email ${CONTACT_EMAIL}.`);
    }
  }

  function onOpenChange(next) {
    setOpen(next);
    if (!next) {
      setStatus("idle");
      setError(null);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button variant={variant} size={size} className={className}>
          {label}
        </Button>
      </DialogTrigger>
      <DialogContent>
        {status === "success" ? (
          <div className="text-center">
            <DialogHeader>
              <DialogTitle>Thanks — we&apos;ll be in touch</DialogTitle>
              <DialogDescription>
                We got your request and will reach out shortly with a quote that
                fits your program.
              </DialogDescription>
            </DialogHeader>
            <Button className="mt-6 w-full" onClick={() => onOpenChange(false)}>
              Close
            </Button>
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Request a quote</DialogTitle>
              <DialogDescription>
                Tell us a bit about your program and we&apos;ll put together a
                quote that fits.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="grid gap-4">
              <div className="grid gap-1.5">
                <Label htmlFor="cd-name">Name</Label>
                <Input
                  id="cd-name"
                  name="name"
                  required
                  autoComplete="name"
                  placeholder="Coach name"
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="cd-email">Email</Label>
                <Input
                  id="cd-email"
                  name="email"
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="you@club.com"
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="cd-message">
                  Message <span className="text-ink-400">(optional)</span>
                </Label>
                <Textarea
                  id="cd-message"
                  name="message"
                  placeholder="Team size, what you're hoping to measure…"
                />
              </div>
              {status === "error" && (
                <p className="text-sm text-[#c0392b]">{error}</p>
              )}
              <Button
                type="submit"
                className="w-full"
                disabled={status === "submitting"}
              >
                {status === "submitting" ? "Sending…" : "Send request"}
              </Button>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

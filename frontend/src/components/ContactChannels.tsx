import { Facebook, Instagram, MessageCircle, Phone } from "lucide-react";
import type { Business } from "@/lib/types";

interface ContactChannelsProps {
  business: Business;
  draftMessage?: string;
}

function digitsOnly(phone: string): string {
  return phone.replace(/[^\d+]/g, "");
}

export function ContactChannels({ business, draftMessage }: ContactChannelsProps) {
  const channels: { label: string; href: string; icon: typeof Phone }[] = [];

  if (business.phone) {
    const phone = digitsOnly(business.phone);
    const encodedMessage = encodeURIComponent(draftMessage ?? "");

    channels.push({ label: "Call", href: `tel:${phone}`, icon: Phone });
    channels.push({
      // wa.me click-to-chat — free, no API, opens WhatsApp with the
      // message pre-filled for you to review and send yourself.
      label: "WhatsApp",
      href: `https://wa.me/${phone.replace("+", "")}${encodedMessage ? `?text=${encodedMessage}` : ""}`,
      icon: MessageCircle,
    });
    channels.push({
      // sms: URI — opens your phone's own texting app with the message
      // pre-filled, uses your own plan, no service or cost involved.
      label: "Text",
      href: `sms:${phone}${encodedMessage ? `?body=${encodedMessage}` : ""}`,
      icon: MessageCircle,
    });
  }

  if (business.facebook_url) {
    channels.push({ label: "Facebook", href: business.facebook_url, icon: Facebook });
  }
  if (business.instagram_url) {
    channels.push({ label: "Instagram", href: business.instagram_url, icon: Instagram });
  }

  if (channels.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {channels.map((channel) => (
        <a
          key={channel.label}
          href={channel.href}
          target={channel.href.startsWith("http") ? "_blank" : undefined}
          rel={channel.href.startsWith("http") ? "noreferrer" : undefined}
          className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs text-ink-muted transition-colors hover:border-brass-dim hover:text-ink"
        >
          <channel.icon size={13} />
          {channel.label}
        </a>
      ))}
    </div>
  );
}
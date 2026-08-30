import Image from "next/image";
import mark from "@/public/swimnetics-mark.png";

// The Swimnetics lockup: mark plus wordmark, one component so Nav and Footer never
// restate the two states.
//
// `inverted` is for the transparent nav over the dark hero gradient. The mark is a flat
// #7200FF raster on transparent with its interior highlight as a transparent hole, so
// brightness(0) invert(1) gives a clean white silhouette. It is a PNG, not a vector, so
// CSS `fill` does nothing and this filter is the only way to recolour it.
//
// The mark sits directly beside the wordmark, so it is decorative: alt="" keeps a screen
// reader from announcing the brand twice.
export default function Brand({ inverted = false }) {
  return (
    <span className="flex items-center gap-2.5">
      <Image
        src={mark}
        alt=""
        width={27}
        height={26}
        priority
        className={inverted ? "[filter:brightness(0)_invert(1)]" : undefined}
      />
      <span
        className={`text-sm font-extrabold tracking-[0.3em] transition-colors ${
          inverted ? "text-white" : "text-ink-900"
        }`}
      >
        SWIMNETICS
      </span>
    </span>
  );
}

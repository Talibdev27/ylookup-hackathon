import { type ButtonHTMLAttributes, forwardRef } from "react";
import clsx from "clsx";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "bg-navy-800 text-white hover:bg-navy-700 shadow-sm",
  secondary: "bg-white text-ink border border-line hover:border-navy-500 hover:text-navy-800",
  ghost: "text-ink-soft hover:text-ink hover:bg-navy-50",
  danger: "bg-bad-bg text-bad hover:bg-bad hover:text-white",
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
};

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }
>(({ className, variant = "primary", size = "md", ...props }, ref) => {
  return (
    <button
      ref={ref}
      className={clsx(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none",
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className
      )}
      {...props}
    />
  );
});
Button.displayName = "Button";

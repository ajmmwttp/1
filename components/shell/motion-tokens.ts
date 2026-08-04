import type { Transition } from "framer-motion";

/** The one easing curve the shell uses — matches --ease-out-expo in globals.css. */
export const EASE_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1];

/** 260ms expo-out: sidebar width, the active rail, every chrome transition. */
export const SHELL_TRANSITION: Transition = { duration: 0.26, ease: EASE_EXPO };

/**
 * The active-nav rail, which moves by `layout` between list items.
 * A spring rather than the expo tween: over 36px the expo curve covers
 * 90% of the travel in the first 90ms and then creeps, which on a 2px
 * mark reads as a teleport. damping 32 against stiffness 380 is a 0.82
 * damping ratio — under 2% overshoot, i.e. half a pixel here. It settles,
 * it does not wobble.
 */
export const RAIL_TRANSITION: Transition = {
  type: "spring",
  stiffness: 380,
  damping: 32,
};

/** Fades for content that appears/disappears with the sidebar width. */
export const FADE_TRANSITION: Transition = { duration: 0.16, ease: EASE_EXPO };

/** Used on the very first commit so a restored localStorage state does not animate in. */
export const NO_TRANSITION: Transition = { duration: 0 };

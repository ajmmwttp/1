import type { Transition } from "framer-motion";

/** The one easing curve the shell uses — matches --ease-out-expo in globals.css. */
export const EASE_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1];

/** 260ms expo-out: sidebar width, the active rail, every chrome transition. */
export const SHELL_TRANSITION: Transition = { duration: 0.26, ease: EASE_EXPO };

/** Fades for content that appears/disappears with the sidebar width. */
export const FADE_TRANSITION: Transition = { duration: 0.16, ease: EASE_EXPO };

/** Used on the very first commit so a restored localStorage state does not animate in. */
export const NO_TRANSITION: Transition = { duration: 0 };

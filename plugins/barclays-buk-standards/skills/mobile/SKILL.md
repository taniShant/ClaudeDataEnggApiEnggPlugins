---
name: mobile
description: BUK mobile coding standards — platform-agnostic principles for iOS and Android. Covers offline behaviour, biometric auth patterns, deep linking, push notifications, and app lifecycle management. Use when implementing or reviewing mobile features. Load alongside a platform-specific extension skill (e.g. barclays-buk-ui-engineer-ios:security-ios) for platform rules.
user-invocable: false
---

# BUK Mobile Standards

> **Placeholder — owned by BUK Mobile Principal Engineers.**
> This skill needs content derived from BUK mobile engineering standards and platform-specific guidelines.
> Platform-specific rules (iOS Swift, Android Kotlin/Compose) should be added as extension skills in the relevant plugin and loaded alongside this base skill.
> See `docs/shared-standards-approach.md` for context on how this skill fits into the shared standards architecture.

---

## Areas to Cover

### Authentication and Session
- Biometric authentication patterns — when to use, fallback to PIN/passcode
- Session expiry — idle timeout, background/foreground transitions
- Re-authentication triggers — high-risk actions, session age
- Jailbreak/root detection response

### Offline Behaviour
- What data may be cached locally and for how long
- Offline-first vs. online-required journey classification
- Error messaging when connectivity is lost
- Sync strategy when connection is restored

### Deep Linking and Navigation
- Approved deep link schemes and universal link patterns
- Authentication state handling on deep link entry
- Back stack management on external entry points

### Push Notifications
- Notification permission request timing and rationale
- Payload structure — required fields, PII exclusion rules
- Silent vs. visible notification usage
- Notification grouping and channel conventions (Android)

### App Lifecycle
- Background task constraints
- Data persistence on app termination
- State restoration on relaunch
- Battery and memory impact considerations

### Accessibility on Mobile
- Touch target minimum sizes
- Dynamic type / font scaling support
- VoiceOver (iOS) and TalkBack (Android) requirements
- See `barclays-buk-standards:accessibility` for full WCAG rules

### Performance
- Cold start time targets
- Frame rate targets for animations (60fps / 120fps ProMotion)
- Image and asset optimisation requirements
- Network request batching and cancellation

---

## Platform Extension Skills

Platform-specific rules are maintained as extension skills in their respective plugins:

| Platform | Extension Skill | Location |
|---|---|---|
| iOS SwiftUI | `barclays-buk-ui-engineer-ios:security-ios` | `plugins/frontend/buk-ui-engineer-ios/skills/security/` |
| Android Jetpack Compose | TBD | `plugins/frontend/buk-ui-engineer-android/` (planned) |

Load this base skill and the relevant extension skill together in agent frontmatter. The extension skill takes precedence for platform-specific rules.

---

## How to Contribute

Raise the source documents with BUK Mobile Principal Engineers. Suggested inputs:

- BUK iOS and Android engineering standards documents
- App security review checklist
- Mobile accessibility requirements document

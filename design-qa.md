# Design QA: choose a Brain location

## Source and target

- Source: the supplied photograph of the existing **Create a Brain** dialog.
- Requested change: preserve the current Notryn dialog style while making the storage location explicit and selectable before creation.

## Visual comparison

- The original width, glass material, type scale, label spacing, close control and footer actions are preserved.
- A second labelled row uses the existing field and folder-icon language, with a visible **Choose** action rather than an unexplained icon.
- After name and location are present, **Brain folder** shows the complete destination without expanding the dialog horizontally.
- The primary action remains disabled until both required choices are present.
- The folder browser uses the same dialog surface and clearly changes its title and confirmation copy for creation.
- The 390 x 844 responsive view keeps the fields, complete-path summary and actions inside the viewport.

## Interaction and accessibility

- Name and path are labelled, the destination is announced as it changes, and the picker remains operable by mouse or keyboard.
- The folder browser starts at local familiar places and allows Home as a creation parent while retaining stricter rules for connecting an existing Brain.
- Reduced-transparency and theme tokens continue to use the shared Notryn styles.

No P0, P1 or P2 visual or interaction defects remain. Minor truncation of very long paths is intentional; the full value remains available in the editable location field and as the summary tooltip.

final result: passed

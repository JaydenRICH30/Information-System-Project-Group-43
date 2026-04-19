# Mobile Acceptance Checklist

## Scope

- Verify customer and merchant flows on mobile width around 360px to 430px.
- Verify desktop layout still looks correct around 1280px and above.

## Global Checks

- No horizontal scrolling on each page.
- Primary buttons wrap or stack instead of overflowing.
- Language switch remains visible and clickable.
- Page titles and subtitles do not overlap.
- Tables are still readable or scroll safely inside their container.
- Cards keep consistent spacing and do not clip shadows or images.

## Page Checklist

### Customer Dashboard

- Check top action buttons stack vertically on narrow screens.
- Check hero search bar collapses to one column.
- Check latest orders section header action stacks below title.
- Check featured product cards stay aligned in one or two columns without overflow.

### Merchant Dashboard

- Check topbar buttons stack cleanly on narrow screens.
- Check operation buttons in the panel header wrap without overlap.
- Check product cards keep price and status aligned.

### Product Catalog

- Check hero area collapses from two columns to one.
- Check filter panel becomes non-sticky and sits above results on mobile.
- Check header nav actions stack full width.
- Check product cards do not overflow and pagination remains tappable.

### Product Detail

- Check gallery thumbnails remain tappable and do not overflow.
- Check purchase box stays readable with quantity controls on mobile.
- Check reviews and related products stack vertically.

### My Cart

- Check top action row stacks vertically.
- Check quantity controls and update button wrap cleanly.
- Check cart table stays usable within table container.
- Check checkout panel falls below cart content on mobile.

### My Orders

- Check toolbar buttons stack if space is tight.
- Check order header status and amount do not overlap.
- Check item cards wrap to one column on narrow screens.

### Order Detail

- Check toolbar actions stack cleanly.
- Check status badge moves below title if needed.
- Check metadata cards and order items wrap correctly.

### Notifications

- Check toolbar buttons stack.
- Check notification title and type badge stack instead of squeezing.
- Check action buttons wrap to multiple rows when needed.

### Merchant Notifications

- Check notification metadata stacks cleanly.
- Check open, mark read, and delete buttons wrap correctly.

### My Account

- Check toolbar buttons stack cleanly.
- Check account badge moves below title block on mobile.
- Check profile and password sections stack vertically.

### Product Management

- Check toolbar wraps cleanly.
- Check image preview grid remains visible and tappable.
- Check form column and product table column stack correctly.

### Orders Management

- Check filter controls stack vertically.
- Check order card content and status controls stay readable.
- Check pagination remains usable on narrow screens.

## Recommended Manual Pass

- Open browser devtools responsive mode.
- Test widths: 390px, 768px, 1280px.
- Test both English and Simplified Chinese.
- Test at least one page with long content and one with empty state.
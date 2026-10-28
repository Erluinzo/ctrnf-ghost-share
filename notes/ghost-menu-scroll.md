# Ghost menu: why the list does not scroll (USA CUSA13795 1.21)

ELF addresses of `CTRNF/out/eboot.elf` (patch XML = + 0x400000). Read from code and assets only; nothing was run.
"Unverified" = not tested in game.

## Cause (verified in code + asset)
The ghost list is an `igGuiList` (UI asset `ui/Octane_MainMenu_GhostSelection.igz`, newest copy in `update2.pak`, object at data +0x12490,
name "GhostList"). Its `_focusScrollMode` is **0 = kFocusScrollNone**. The track list (`ui/Octane_LevelSelect_Proto.igz`, "LevelList") has **2 = kFocusScrollCentered**.
Enum `ListFocusScrollMode` (names 0x2430750): 0 None, 1 ToFit, 2 Centered.
List update 0x261900 (called from 0x25fe56): `cmp byte [list+0x329],0; je skip` (0x2619aa), `cmp dword [list+0x74],0; je skip` (0x2619b3),
else 0x2653c0 computes the scroll to the focused item. With mode 0 the focus moves but the list never scrolls. No limit/visible-count field is involved.

## igGuiList fields (size 0x350, reflection cb 0x16abbf0, vtable ptr stored in objects = 0x2436b18)
+0x20 _templateItem, +0x30 _listItemPopulator, +0x40 _margin (left, top, right, bottom floats), +0x50 _padding (same order),
+0x60 _itemShiftSpeed, +0x64 _scrollSpeed, +0x68 _horizontalScroll (byte), +0x69 _listWrap, +0x6a _acceptDpadInput, +0x6c _alignmentMode,
+0x70 _sortMode, **+0x74 _focusScrollMode**, +0x78 _touchScrollMode, +0x7c _scissorListBounds (byte), +0x7d _alwaysCreatePlaceables,
+0x7e _unifyFocus, +0x8c _itemAutoScaleMode, +0x90 _previewListItemCount, +0x94 _scrollPercentage, +0xc0 _rootPlaceable,
+0xc8 _scrollPlaceable, +0xd0 _items, +0xe0 _visibleItems, +0x130.. _focusItem[16], +0x324 _scrollSize, +0x328 _unboundedFocusScroll,
+0x329 _updateFocusScroll (set on focus change at 0x261359, cleared when the scroll is done 0x26570a), +0x32a _placeablesDirty.
igGuiListItem: +0x28 _min, +0x30 _max (vec2, list space). igGuiEventListAdd: +0x18 _list (= the list's **placeable**, not the igGuiList), +0x20 _listItem.

| Field | Ghost list | Track list |
|---|---|---|
| _margin (l,t,r,b) | 2.5, -23, 2.5, 2.5 | 0, 0, 0, 0 |
| _padding (l,t,r,b) | 0, 0, 0, -30.5 | 150, 15, 0, 35 |
| _scrollSpeed | 500 | 1400 |
| _sortMode | 1 (ByDistanceFromCenter) | 0 |
| _focusScrollMode | **0** | **2** |
| _previewListItemCount | 5 | 10 |
| _scissorListBounds | 0 | 0 |
Both: _touchScrollMode 0, _alwaysCreatePlaceables 1, _unifyFocus 1, _unboundedFocusScroll/_updateFocusScroll 1.

Math (from 0x264c90 layout, 0x2653c0 ToFit, vertical list):
- Layout: first item at y = margin.top + padding.top; each item takes its height + padding.top + padding.bottom (ghost rows overlap 30.5).
  margin.bottom (+0x4c) is used only by the focus-fit check (not by layout).
- ToFit (mode 1): view = [s, s + H], s = -scrollPlaceable.y, H = list placeable height / scale.
  Scrolls only if `item.min.y - (pad.top + margin.top) < s` or `item.max.y + pad.bottom + margin.bottom > s + H`, by the smallest amount,
  at _scrollSpeed px/s (first time instant). Back on Confirm: -23 + 23 = 0, so the scroll returns exactly to the original layout.
- Centered (mode 2): always centers the focused item, no clamp seen; Confirm would move to the middle. Not wanted here.

List placeable (asset handle 0x80000002 = EXNM "GhostList"): igz placeable +0x1020, extent 648 x 770, pos (13,-34) in parent +0x1140
(pos 510,50, anchors 2,2). Guess (unverified): screen y ~171..941. Button legend bar (+0x13c0, "octane_ui_buttonlegend_bg_tga")
132 tall at the bottom, top ~938-948. Current fit limit = list bottom + 28 (pad.b -30.5 + margin.b 2.5) ~ y 969, so with ToFit alone
the last row may still end ~30 px under the legend.

## Fix options (ranked)
1. **Runtime code, recommended.** After the menu is built, write to the igGuiList:
   - `dword [list+0x74] = 1` (kFocusScrollToFit). Read every update, so a runtime write works.
   - `float [list+0x4c]` (margin.bottom) = 32.5 (`0x42020000`) as a start, so the fit limit is about the legend top. Tune 30-60 in game.
   Getting `list`:
   - In the existing populate hook (call sites 0x9e2756 / 0x9e2d22, `call cave`): populate 0x9e23d0 starts `push rbp; mov rbp,rsp; push r15`,
     and its only caller 0x25f6f7 (in igGuiList method 0x25f5f0, vtable slot at 0x2436be0) has r15 = the igGuiList.
     So in the cave, before rbp changes: `mov rax, [rbp-8]` = igGuiList. Guard: `[rax] == 0x2436b18` (runtime: compare with a RIP-relative
     address, = patch 0x2836b18) and `[rax+0x30] == populator` if handy. Populate runs before the layout (0x25f9c6) in the same call.
   - Or at populate entry: r15 = igGuiList, rdx = [r15+0xd0] (items list) as a guard.
   - Or in the item ListAdd branch 0x9b3a27 (`49 8b 5d 20 48 85 db 0f 85 a1 01 00 00`, jump target, rax free):
     `list = [[r13+0x18]+0x38]` (placeable._asset) - unverified that _asset holds the pointer at run time; prefer the populate way.
   Risks (unverified): no scissor, so after scrolling ~100 px the top row (Confirm) moves up by that much and may overlap the title area;
   whether rows outside the list bounds are hidden is unknown. `_scissorListBounds` (+0x7c byte = 1) would clip, but the first row already
   starts 23 px above the list top (margin.top -23), so it would cut Confirm even without scrolling. Try without it first.
2. **Asset change** (same fields, no code): `update2.pak` `ui/Octane_MainMenu_GhostSelection.igz` file offsets
   _focusScrollMode 0x16bec (`00000000` -> `01000000`), margin.bottom 0x16bc4 (`00002040` = 2.5), padding.bottom 0x16bd4 (`0000f4c1` = -30.5).
   Needs a repacked/overridden pak (mod system); more work and more risk than option 1.
3. **No scrolling: move or pack rows.** margin.top (+0x44, now -23) more negative moves every row up; padding.bottom (+0x5c) more negative
   packs rows (now 131.5 px per ghost row for 128 px cards, so rows would overlap). Both are read by layout 0x264c90, so set them before it runs
   (populate hook). Only fits about one extra row; looks worse. Use only if option 1 fails.
4. mode 2 (Centered) like the track list: works, but recenters on every move and pushes Confirm to the middle. Not recommended.

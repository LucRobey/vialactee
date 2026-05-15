/** 5×5 stud bitmaps: 1 = 1×1 flat tile, 0 = empty (red brick shows through). */
const LETTER_5X5: Record<string, number[][]> = {
  D: [
    [1, 1, 1, 1, 0],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [1, 1, 1, 1, 0],
  ],
  R: [
    [1, 1, 1, 1, 0],
    [1, 0, 0, 0, 1],
    [1, 1, 1, 1, 0],
    [1, 0, 1, 0, 0],
    [1, 0, 0, 1, 1],
  ],
  O: [
    [0, 1, 1, 1, 0],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [0, 1, 1, 1, 0],
  ],
  P: [
    [1, 1, 1, 1, 0],
    [1, 0, 0, 0, 1],
    [1, 1, 1, 1, 0],
    [1, 0, 0, 0, 0],
    [1, 0, 0, 0, 0],
  ],
};

const LETTER_GAP_STUDS = 1;

export type DropTileVariant = 'white' | 'yellow' | 'grey' | 'clear';

export type DropTilePlacement = {
  col: number;
  row: number;
  variant: DropTileVariant;
  rotationDeg: number;
};

const tileVariant = (tileIndex: number): DropTileVariant => {
  if ([4, 11, 18, 27, 34].includes(tileIndex)) return 'clear';
  if (tileIndex === 8 || tileIndex === 24) return 'yellow';
  if (tileIndex === 16) return 'grey';
  return 'white';
};

const tileRotation = (tileIndex: number): number => ((tileIndex * 17) % 15) - 7;

/** Placements for "DROP" on a local stud grid (origin top-left). */
export const buildDropWordPlacements = (): DropTilePlacement[] => {
  const placements: DropTilePlacement[] = [];
  let offsetCol = 0;
  let tileIndex = 0;

  for (const char of 'DROP') {
    const bitmap = LETTER_5X5[char];
    if (!bitmap) continue;

    bitmap.forEach((row, rowIndex) => {
      row.forEach((cell, colIndex) => {
        if (!cell) return;
        placements.push({
          col: offsetCol + colIndex,
          row: rowIndex,
          variant: tileVariant(tileIndex),
          rotationDeg: tileRotation(tileIndex),
        });
        tileIndex += 1;
      });
    });

    offsetCol += bitmap[0].length + LETTER_GAP_STUDS;
  }

  return placements;
};

export const DROP_WORD_WIDTH_STUDS = (() => {
  let w = 0;
  for (const char of 'DROP') {
    const bitmap = LETTER_5X5[char];
    if (!bitmap) continue;
    w += bitmap[0].length + LETTER_GAP_STUDS;
  }
  return w - LETTER_GAP_STUDS;
})();

export const DROP_WORD_HEIGHT_STUDS = 5;

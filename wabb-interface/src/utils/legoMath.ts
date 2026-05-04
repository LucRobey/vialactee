export const LEGO_MATH = {
  STUD: 30,         // 1 Stud = exactly 30px
  TOLERANCE: 4,     // The microscopic 4px physical gap between touching pieces

  // 1. Math for Conceptual Containers (Grid layout width/height)
  grid: (studs: number) => studs * 30,

  // 2. Math for Physical Rendered Pieces (Total footprint minus tolerance gap)
  physicalSize: (studs: number) => (studs * 30) - 4,

  // 3. Math for Absolute Map Positioning (Centers the piece within its conceptual trench)
  position: (studIndex: number) => (studIndex * 30) + 2,
};

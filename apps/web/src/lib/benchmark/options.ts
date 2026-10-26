const MIB = 1024 * 1024;

// Server limits: size 1 KiB..10 MiB, iterations 1..10.
export const SIZE_OPTIONS = [1, 2, 5, 10].map((mib) => ({
  value: mib * MIB,
  label: `${mib} MB`,
}));

export const ITERATION_OPTIONS = [1, 3, 5, 10].map((n) => ({
  value: n,
  label: `${n} putaran`,
}));

export const DEFAULT_SIZE = 1 * MIB;
export const DEFAULT_ITERATIONS = 5;

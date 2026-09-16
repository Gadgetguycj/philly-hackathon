// QR encoder: byte mode, error correction level M, versions 1 to 10.
const QR = (() => {
  const EC = {
    1: [10, 1, 16, 0, 0], 2: [16, 1, 28, 0, 0], 3: [26, 1, 44, 0, 0], 4: [18, 2, 32, 0, 0],
    5: [24, 2, 43, 0, 0], 6: [16, 4, 27, 0, 0], 7: [18, 4, 31, 0, 0], 8: [22, 2, 38, 2, 39],
    9: [22, 3, 36, 2, 37], 10: [26, 4, 43, 1, 44],
  };
  const ALIGNMENT = {
    1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
    6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50],
  };
  const EXP = new Uint8Array(512);
  const LOG = new Uint8Array(256);
  for (let i = 0, value = 1; i < 255; i++) {
    EXP[i] = value; LOG[value] = i;
    value = (value << 1) ^ (value & 0x80 ? 0x11d : 0);
  }
  for (let i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
  const mul = (a, b) => (a === 0 || b === 0 ? 0 : EXP[LOG[a] + LOG[b]]);

  const dataCodewords = version => {
    const [, blocks1, size1, blocks2, size2] = EC[version];
    return blocks1 * size1 + blocks2 * size2;
  };

  function generator(degree) {
    let poly = [1];
    for (let i = 0; i < degree; i++) {
      const next = new Array(poly.length + 1).fill(0);
      for (let j = 0; j < poly.length; j++) {
        next[j] ^= poly[j];
        next[j + 1] ^= mul(poly[j], EXP[i]);
      }
      poly = next;
    }
    return poly;
  }

  function remainder(data, degree) {
    const poly = generator(degree);
    const result = new Uint8Array(degree);
    for (const byte of data) {
      const factor = byte ^ result[0];
      result.copyWithin(0, 1);
      result[degree - 1] = 0;
      for (let i = 0; i < degree; i++) result[i] ^= mul(poly[i + 1], factor);
    }
    return result;
  }

  function pickVersion(byteLength) {
    for (let version = 1; version <= 10; version++) {
      const header = 4 + (version >= 10 ? 16 : 8);
      if (dataCodewords(version) * 8 >= header + byteLength * 8) return version;
    }
    throw new Error('The text is too long for this QR encoder.');
  }

  function codewords(text) {
    const bytes = new TextEncoder().encode(text);
    const version = pickVersion(bytes.length);
    const total = dataCodewords(version);
    const bits = [];
    const push = (value, length) => {
      for (let i = length - 1; i >= 0; i--) bits.push((value >> i) & 1);
    };
    push(4, 4);
    push(bytes.length, version >= 10 ? 16 : 8);
    for (const byte of bytes) push(byte, 8);
    for (let i = 0; i < Math.min(4, total * 8 - bits.length); i++) bits.push(0);
    while (bits.length % 8) bits.push(0);
    const data = new Uint8Array(total);
    for (let i = 0; i < bits.length; i += 8) {
      data[i / 8] = bits.slice(i, i + 8).reduce((acc, bit) => (acc << 1) | bit, 0);
    }
    for (let i = bits.length / 8, pad = 0; i < total; i++, pad++) data[i] = pad % 2 ? 0x11 : 0xec;
    return { version, data };
  }

  function interleave(version, data) {
    const [ecPerBlock, blocks1, size1, blocks2, size2] = EC[version];
    const blocks = [];
    let offset = 0;
    for (let i = 0; i < blocks1 + blocks2; i++) {
      const size = i < blocks1 ? size1 : size2;
      const block = data.slice(offset, offset + size);
      offset += size;
      blocks.push({ data: block, ec: remainder(block, ecPerBlock) });
    }
    const result = [];
    for (let i = 0; i < Math.max(size1, size2); i++) {
      for (const block of blocks) if (i < block.data.length) result.push(block.data[i]);
    }
    for (let i = 0; i < ecPerBlock; i++) for (const block of blocks) result.push(block.ec[i]);
    return result;
  }

  function functionModules(version) {
    const size = version * 4 + 17;
    const modules = Array.from({ length: size }, () => new Uint8Array(size));
    const reserved = Array.from({ length: size }, () => new Uint8Array(size));
    const set = (row, column, value) => {
      modules[row][column] = value;
      reserved[row][column] = 1;
    };
    const finder = (row, column) => {
      for (let r = -1; r <= 7; r++) {
        for (let c = -1; c <= 7; c++) {
          const y = row + r;
          const x = column + c;
          if (y < 0 || y >= size || x < 0 || x >= size) continue;
          const ring = Math.max(Math.abs(r - 3), Math.abs(c - 3));
          set(y, x, ring === 2 || ring > 3 ? 0 : 1);
        }
      }
    };
    finder(0, 0);
    finder(0, size - 7);
    finder(size - 7, 0);
    for (let i = 7; i < size - 7; i++) {
      const value = i % 2 === 0 ? 1 : 0;
      set(6, i, value);
      set(i, 6, value);
    }
    const centers = ALIGNMENT[version];
    for (const row of centers) {
      for (const column of centers) {
        const nearFinder =
          (row <= 8 && column <= 8) || (row <= 8 && column >= size - 9) || (row >= size - 9 && column <= 8);
        if (nearFinder) continue;
        for (let r = -2; r <= 2; r++) {
          for (let c = -2; c <= 2; c++) {
            set(row + r, column + c, Math.max(Math.abs(r), Math.abs(c)) === 1 ? 0 : 1);
          }
        }
      }
    }
    for (let i = 0; i <= 8; i++) {
      if (i !== 6) { reserved[8][i] = 1; reserved[i][8] = 1; }
    }
    for (let i = 0; i < 8; i++) { reserved[8][size - 1 - i] = 1; reserved[size - 1 - i][8] = 1; }
    set(size - 8, 8, 1);
    if (version >= 7) {
      let bits = version;
      for (let i = 0; i < 12; i++) bits = (bits << 1) ^ ((bits >> 11) * 0x1f25);
      const value = (version << 12) | bits;
      for (let i = 0; i < 18; i++) {
        const bit = (value >> i) & 1;
        set(Math.floor(i / 3), size - 11 + (i % 3), bit);
        set(size - 11 + (i % 3), Math.floor(i / 3), bit);
      }
    }
    return { size, modules, reserved };
  }

  function placeData(size, reserved, stream) {
    const data = Array.from({ length: size }, () => new Uint8Array(size));
    let index = 0;
    for (let right = size - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (let vertical = 0; vertical < size; vertical++) {
        for (let column of [right, right - 1]) {
          const upward = ((right + 1) & 2) === 0;
          const row = upward ? size - 1 - vertical : vertical;
          if (reserved[row][column]) continue;
          const bit = index < stream.length * 8 ? (stream[index >> 3] >> (7 - (index & 7))) & 1 : 0;
          data[row][column] = bit;
          index++;
        }
      }
    }
    return data;
  }

  const maskBit = (mask, row, column) => {
    switch (mask) {
      case 0: return (row + column) % 2 === 0;
      case 1: return row % 2 === 0;
      case 2: return column % 3 === 0;
      case 3: return (row + column) % 3 === 0;
      case 4: return (Math.floor(row / 2) + Math.floor(column / 3)) % 2 === 0;
      case 5: return ((row * column) % 2) + ((row * column) % 3) === 0;
      case 6: return (((row * column) % 2) + ((row * column) % 3)) % 2 === 0;
      default: return (((row + column) % 2) + ((row * column) % 3)) % 2 === 0;
    }
  };

  function drawFormat(modules, size, mask) {
    const data = mask; // Error correction level M is 0b00, so the format data is the mask number.
    let rest = data;
    for (let i = 0; i < 10; i++) rest = (rest << 1) ^ ((rest >> 9) * 0x537);
    const value = ((data << 10) | rest) ^ 0x5412;
    const bit = index => (value >> index) & 1;
    for (let i = 0; i <= 5; i++) modules[i][8] = bit(i);
    modules[7][8] = bit(6);
    modules[8][8] = bit(7);
    modules[8][7] = bit(8);
    for (let i = 9; i < 15; i++) modules[8][14 - i] = bit(i);
    for (let i = 0; i < 8; i++) modules[8][size - 1 - i] = bit(i);
    for (let i = 8; i < 15; i++) modules[size - 15 + i][8] = bit(i);
    modules[size - 8][8] = 1;
  }

  function lineRuns(line) {
    let score = 0;
    let run = 1;
    for (let i = 1; i < line.length; i++) {
      if (line[i] === line[i - 1]) {
        run++;
        if (run === 5) score += 3;
        else if (run > 5) score += 1;
      } else run = 1;
    }
    const finder = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0];
    for (let i = 0; i + 11 <= line.length; i++) {
      const window = line.slice(i, i + 11);
      if (finder.every((bit, index) => window[index] === bit)) score += 40;
      if (finder.every((bit, index) => window[10 - index] === bit)) score += 40;
    }
    return score;
  }

  function penalty(modules, size) {
    let score = 0;
    let dark = 0;
    for (let row = 0; row < size; row++) {
      score += lineRuns(Array.from(modules[row]));
      score += lineRuns(modules.map(line => line[row]));
      for (let column = 0; column < size; column++) dark += modules[row][column];
    }
    for (let row = 0; row + 1 < size; row++) {
      for (let column = 0; column + 1 < size; column++) {
        const value = modules[row][column];
        if (
          value === modules[row][column + 1] &&
          value === modules[row + 1][column] &&
          value === modules[row + 1][column + 1]
        ) score += 3;
      }
    }
    const percent = (dark * 100) / (size * size);
    return score + Math.floor(Math.abs(percent - 50) / 5) * 10;
  }

  function matrix(text) {
    const { version, data } = codewords(text);
    const stream = interleave(version, data);
    const base = functionModules(version);
    const placed = placeData(base.size, base.reserved, stream);
    let best = null;
    for (let mask = 0; mask < 8; mask++) {
      const candidate = base.modules.map(row => Uint8Array.from(row));
      for (let row = 0; row < base.size; row++) {
        for (let column = 0; column < base.size; column++) {
          if (base.reserved[row][column]) continue;
          candidate[row][column] = placed[row][column] ^ (maskBit(mask, row, column) ? 1 : 0);
        }
      }
      drawFormat(candidate, base.size, mask);
      const score = penalty(candidate, base.size);
      if (!best || score < best.score) best = { score, mask, version, modules: candidate };
    }
    return best;
  }

  function draw(canvas, text, moduleSize = 6, quiet = 4) {
    const { modules } = matrix(text);
    const side = modules.length;
    const pixels = (side + quiet * 2) * moduleSize;
    canvas.width = pixels;
    canvas.height = pixels;
    const context = canvas.getContext('2d');
    context.fillStyle = '#ffffff';
    context.fillRect(0, 0, pixels, pixels);
    context.fillStyle = '#000000';
    for (let row = 0; row < side; row++) {
      for (let column = 0; column < side; column++) {
        if (modules[row][column]) {
          context.fillRect((column + quiet) * moduleSize, (row + quiet) * moduleSize, moduleSize, moduleSize);
        }
      }
    }
    return side;
  }

  return { matrix, draw };
})();

if (typeof module !== 'undefined') module.exports = QR;

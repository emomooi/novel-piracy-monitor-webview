const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync(process.argv[2], 'utf8');

function between(start, end) {
  const first = html.indexOf(start);
  const last = html.indexOf(end, first);
  assert.notEqual(first, -1, `missing source marker: ${start}`);
  assert.notEqual(last, -1, `missing end marker: ${end}`);
  return html.slice(first, last);
}

const source = [
  between('function getAllRows() {', '  /* ==================== 框选状态'),
  between('function parseDateKey(dateStr) {', '  /* 白名单行沉底 +'),
  between('function compareRowsByDisplayOrder(a, b) {', '  /* 白名单行沉底 +'),
  between('window.reorderRows = function () {', '  /* ======================================================================'),
  between('function applyFilterToRow(r) {', '  window.applyFilters = function () {'),
  between('window.applyFilters = function () {', '  /* 来源页签点击'),
  between('window.appendRow = function (jsonStr) {', '  /* 行点击核心'),
].join('\n');

class FakeClassList {
  constructor() {
    this.values = new Set();
  }

  add(...names) {
    names.forEach((name) => this.values.add(name));
  }

  remove(...names) {
    names.forEach((name) => this.values.delete(name));
  }

  contains(name) {
    return this.values.has(name);
  }

  toggle(name, force) {
    const shouldAdd = force === undefined ? !this.values.has(name) : !!force;
    if (shouldAdd) this.values.add(name);
    else this.values.delete(name);
    return shouldAdd;
  }
}

class FakeNode {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.dataset = {};
    this.classList = new FakeClassList();
    this.style = {};
    this.attributes = {};
    this.listeners = {};
    this.parentNode = null;
    this.textContent = '';
    this.title = '';
    this.checked = false;
  }

  set className(value) {
    this.classList = new FakeClassList();
    this.classList.add(...String(value).split(/\s+/).filter(Boolean));
  }

  get className() {
    return Array.from(this.classList.values).join(' ');
  }

  appendChild(child) {
    if (child.parentNode) {
      const previous = child.parentNode.children.indexOf(child);
      if (previous >= 0) child.parentNode.children.splice(previous, 1);
    }
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  insertBefore(child, reference) {
    if (child.parentNode) {
      const previous = child.parentNode.children.indexOf(child);
      if (previous >= 0) child.parentNode.children.splice(previous, 1);
    }
    const index = this.children.indexOf(reference);
    assert.notEqual(index, -1);
    child.parentNode = this;
    this.children.splice(index, 0, child);
    return child;
  }

  addEventListener(name, callback) {
    this.listeners[name] = callback;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  set innerHTML(value) {
    assert.equal(value, '');
    this.children.forEach((child) => { child.parentNode = null; });
    this.children = [];
  }
}

function makeEnvironment(optimized) {
  const tbody = new FakeNode('div');
  const historyButton = new FakeNode('button');
  const tableScroll = {
    scrollHeight: 100,
    scrollTop: 0,
    clientHeight: 100,
  };
  const window = {};
  const document = {
    getElementById(id) {
      if (id === 'tableBody') return tbody;
      if (id === 'btnTbHistory') return historyButton;
      return null;
    },
    querySelectorAll(selector) {
      assert.equal(selector, '#tableBody .table-row');
      return tbody.children.filter((row) => row.classList.contains('table-row'));
    },
    querySelector(selector) {
      return selector === '.table-scroll' ? tableScroll : null;
    },
    createElement(tagName) {
      return new FakeNode(tagName);
    },
  };
  const context = {
    window,
    document,
    tableBody: tbody,
    tableScroll,
    _lastAnchorRowIdx: null,
    _currentTabFilter: '百度',
    _searchBoxFilter: '目标',
    TAB_ALL: '全部',
    TAB_GROUPS: {
      '百度': ['百度', '百度移动版'],
      '知道': ['知道', '知道移动版'],
      '头条': ['头条', '头条移动版'],
      '搜狗': ['搜狗', '搜狗移动版'],
      '360': ['360', '360移动版'],
    },
    makeCell(label, className, text) {
      const cell = new FakeNode('div');
      cell.className = className;
      cell.textContent = text === null || text === undefined ? '' : String(text);
      return cell;
    },
    makeUrlCell(url) {
      const cell = new FakeNode('div');
      cell.className = 'td col-url';
      cell.textContent = url === null || url === undefined ? '' : String(url);
      return cell;
    },
    syncCheckAllState() {},
    handleRowClick() {},
  };
  vm.createContext(context);

  let appendSource = between(
    'window.appendRow = function (jsonStr) {',
    '  /* 行点击核心',
  );
  if (!optimized) {
    const optimizedRefresh = `    insertRowInOrder(row);
    applyFilterToRow(row);`;
    assert.ok(appendSource.includes(optimizedRefresh), 'optimized append path changed');
    appendSource = appendSource.replace(
      optimizedRefresh,
      `    window.reorderRows();
    if (typeof window.applyFilters === 'function') { window.applyFilters(); }`,
    );
  }

  vm.runInContext(`${source}\n${appendSource}`, context);
  window.appendLog = function () {};
  const counters = { getAllRows: 0, reorderRows: 0, applyFilters: 0, filterRow: 0 };
  const originalGetAllRows = context.getAllRows;
  context.getAllRows = function () {
    counters.getAllRows += 1;
    return originalGetAllRows();
  };
  const originalFilterRow = context.applyFilterToRow;
  context.applyFilterToRow = function (row) {
    counters.filterRow += 1;
    return originalFilterRow(row);
  };
  const originalReorderRows = window.reorderRows;
  window.reorderRows = function () {
    counters.reorderRows += 1;
    return originalReorderRows();
  };
  const originalApplyFilters = window.applyFilters;
  window.applyFilters = function () {
    counters.applyFilters += 1;
    return originalApplyFilters();
  };
  return { context, tbody, window, counters, historyButton };
}

function makeRows() {
  const sources = ['百度', '百度移动版', '知道', '头条', '搜狗'];
  const rows = [];
  for (let i = 0; i < 80; i += 1) {
    rows.push({
      source: sources[i % sources.length],
      title: i % 11 === 0 ? '' : `结果 ${i}${i % 7 === 0 ? ' 目标词' : ''}`,
      summary: i % 13 === 0 ? '' : `摘要 ${i}${i % 9 === 0 ? ' 目标词' : ''}`,
      date: i % 10 === 0
        ? '未知'
        : i % 3 === 0
          ? '2026年10月26日'
          : `2026-${String(1 + (i % 9)).padStart(2, '0')}-${String(1 + (i % 27)).padStart(2, '0')}`,
      url: i % 8 === 0 ? 'https://duplicate.example/item' : `https://example.test/${i}`,
      book: `作品 ${i % 5}`,
      keyword: `关键词 ${i % 4}`,
      srcId: `source-${i % 5}`,
      isNew: i % 6 === 0,
      is_white: i % 7 === 0,
    });
  }
  rows.push({
    source: '百度',
    title: '',
    summary: '',
    date: '不可解析',
    url: 'https://duplicate.example/item',
    book: '',
    keyword: '',
    srcId: '',
    is_white: true,
  });
  return rows;
}

function snapshot(tbody) {
  return tbody.children.map((row) => ({
    dataset: { ...row.dataset },
    classes: Array.from(row.classList.values).sort(),
    display: row.style.display || '',
    content: row.children.map((cell) => ({
      className: cell.className,
      text: cell.textContent,
      title: cell.title,
      checked: cell.checked,
    })),
  }));
}

async function testHistoryWhitelistRows() {
  const environment = makeEnvironment(true);
  const records = [
    {
      url: 'https://example.test/white-a',
      book: '白名单作品 A',
      source: '百度',
      is_white: true,
    },
    {
      url: 'https://example.test/plain',
      book: '普通作品',
      source: '知道',
      is_white: false,
    },
    {
      url: 'https://example.test/white-b',
      book: '白名单作品 B',
      source: '搜狗',
      is_white: true,
    },
  ];
  environment.window.pywebview = {
    api: {
      load_history() {
        return Promise.resolve(records);
      },
    },
  };
  environment.context.requireApi = () => true;
  const historySource = between(
    'var btnTbOpen = document.getElementById',
    '  /* ==================== 清 cookies',
  );
  vm.runInContext(historySource, environment.context);
  assert.equal(typeof environment.historyButton.listeners.click, 'function');
  environment.historyButton.listeners.click();
  await new Promise((resolve) => setImmediate(resolve));

  const rows = snapshot(environment.tbody);
  assert.equal(rows.length, records.length);
  assert.deepEqual(
    rows.map((row) => row.dataset.url),
    [
      'https://example.test/plain',
      'https://example.test/white-a',
      'https://example.test/white-b',
    ],
    'history rows must keep non-white rows first and white rows at the bottom',
  );
  const whiteRows = rows.filter((row) => row.classes.includes('row-white'));
  assert.equal(whiteRows.length, 2);
  assert.deepEqual(
    whiteRows.map((row) => row.dataset.whiteCommon),
    ['1', '1'],
  );
}

const records = makeRows();
const baseline = makeEnvironment(false);
const optimized = makeEnvironment(true);
records.forEach((record) => {
  baseline.window.appendRow(JSON.stringify(record));
  optimized.window.appendRow(JSON.stringify(record));
});

const before = snapshot(baseline.tbody);
const after = snapshot(optimized.tbody);
assert.equal(after.length, before.length, 'row counts differ');
assert.deepEqual(after, before, 'ordered row content, datasets, visibility, or selection differ');

const whiteIndexes = after
  .map((row, index) => row.classes.includes('row-white') ? index : -1)
  .filter((index) => index >= 0);
assert.ok(
  whiteIndexes.every((index, position) => index === after.length - whiteIndexes.length + position),
  'white rows are not grouped at the bottom',
);

const visibleBaseline = before.filter((row) => row.display !== 'none');
const visibleOptimized = after.filter((row) => row.display !== 'none');
assert.deepEqual(visibleOptimized, visibleBaseline, 'visible row sets differ');
assert.equal(baseline.counters.reorderRows, records.length * 2);
assert.equal(baseline.counters.getAllRows, records.length * 3);
assert.equal(baseline.counters.filterRow, records.length * (records.length + 1) / 2);
assert.equal(optimized.counters.reorderRows, 0);
assert.equal(optimized.counters.getAllRows, 0);
assert.equal(optimized.counters.applyFilters, 0);
assert.equal(optimized.counters.filterRow, records.length);

console.log('frontend row equivalence: OK');
testHistoryWhitelistRows()
  .then(() => console.log('frontend history whitelist: OK'))
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });

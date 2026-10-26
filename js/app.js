
/* ======================================================================
   批 1-1：搜索启动骨架
   - Python 侧用 window.evaluate_js("window.appendLog('...')") 主动推送
   - 本文件负责：收集界面输入 → 校验 → 调 start_search；并接收 setSearching
     / appendLog 两个 Python 回调把界面画出来
   ====================================================================== */
(function () {
  'use strict';

  var logBody = document.getElementById('logBody');
  var tableBody = document.getElementById('tableBody');
  var tableScroll = document.querySelector('.table-scroll');
  var bookInput = document.getElementById('bookInput');
  var pagesInput = document.getElementById('pagesInput');
  var btnSearch = document.getElementById('btnSearch');
  var btnSearchStop = document.getElementById('btnStop');
  var btnTbClear = document.getElementById('btnTbClear');
  var btnTbWhite = document.getElementById('btnTbWhite');
  var btnTbResetWhite = document.getElementById('btnTbResetWhite');
  var btnTbSelectAll = document.getElementById('btnTbSelectAll');
  var checkAllRow = document.getElementById('checkAllRow');
  var tableSearchInput = document.getElementById('tableSearchInput');
  var btnTbSearchClear = document.getElementById('btnTbSearchClear');

  /* ==================== 常量区 ==================== */
  /* 页签哨兵值：表示「不过滤来源」 */
  var TAB_ALL = '全部';

  /* 右键菜单「打开源链接」用的引擎搜索页 URL（只挪位置，不改内容） */
  var ENGINE_URL = {
    'baidu':          'https://www.baidu.com/s?wd=',
    'baidu_mobile':   'https://m.baidu.com/s?word=',
    'sogou_pc':       'https://www.sogou.com/web?query=',
    'sogou_mobile':   'https://m.sogou.com/web/searchList.jsp?keyword=',
    'so360_pc':       'https://www.so.com/s?q=',
    'so360_mobile':   'https://m.so.com/s?q=',
    'bing':           'https://www.bing.com/search?q=',
    'toutiao_pc':     'https://so.toutiao.com/search?keyword=',
    'toutiao_mobile': 'https://so.toutiao.com/search?keyword=',
    'zhidao':         'https://zhidao.baidu.com/search?word=',
    'zhidao_mobile':  'https://zhidao.baidu.com/search?word=',
    'tieba':          'https://tieba.baidu.com/f/search/res?qw=',
    'sogou_weixin':   'https://weixin.sogou.com/weixin?type=2&query=',
    'weibo_mobile':   'https://s.weibo.com/weibo?q='
  };

  /* ==================== 行多选状态（批 4-A-1） ==================== */
  var _lastAnchorRowIdx = null;   // 上次点击的行序号（Shift 区间用）

  /* 当前所有结果行（按 DOM 顺序） */
  function getAllRows() {
    return Array.prototype.slice.call(
      document.querySelectorAll('#tableBody .table-row')
    );
  }

  /* ==================== 框选状态（批 4-A-2） ==================== */
  var _drag = {
    active: false,              // 移动超阈值后为 true（才算框选）
    startX: 0,
    startY: 0,
    curX: 0,
    curY: 0,
    suppressNextClick: false,   // 框选结束后要吞掉随之而来的 click
    autoScrollTimer: null,      // 触边自动滚的定时器
    autoScrollDir: 0
  };
  var DRAG_THRESHOLD = 6;       // 移动超过 6px 才算框选

  /* ==================== 行右键菜单状态（批 4-A-3） ==================== */
  var _ctxTargetRow = null;     // 当前菜单作用的行元素

  /* ==================== 筛选状态（批 4-A-4） ==================== */
  var _currentTabFilter = TAB_ALL;   // 当前来源页签
  var _searchBoxFilter = '';        // 工具栏搜索框关键词（小写）

  /* 取"作用行集合"：有选中行 → 所有选中行；否则 → 当前行 */
  function getActionRows() {
    var all = getAllRows();
    var selected = all.filter(function (r) {
      var cb = r.querySelector('input[type=checkbox].row-check');
      return cb && cb.checked;
    });
    if (selected.length > 0) { return selected; }
    if (_ctxTargetRow && all.indexOf(_ctxTargetRow) >= 0) { return [_ctxTargetRow]; }
    return [];
  }

  function pad2(n) { return (n < 10 ? '0' : '') + n; }

  function nowStamp() {
    var d = new Date();
    return pad2(d.getHours()) + ':' + pad2(d.getMinutes()) + ':' + pad2(d.getSeconds());
  }

  /* Python 调用的入口：追加一行日志并滚到底部 */
  window.appendLog = function (text) {
    var line = document.createElement('div');
    line.className = 'log-line';

    var msg = (text === null || text === undefined) ? '' : String(text);

    // 文本里已经带 [HH:MM:SS] 前缀就不重复加
    if (/^\[\d{2}:\d{2}:\d{2}\]/.test(msg)) {
      line.textContent = msg;
    } else {
      line.textContent = '[' + nowStamp() + '] ' + msg;
    }

    if (msg.indexOf('[暂停]') !== -1) { line.classList.add('alert'); }

    if (msg.indexOf('[!!]') !== -1) { line.classList.add('warn'); }

    logBody.appendChild(line);
    logBody.scrollTop = logBody.scrollHeight;   // 自动滚到最新一行
    return logBody.children.length;
  };

  /* ======================================================================
     Python 调用的入口：往结果表格追加一行
     Python 侧：window.evaluate_js('window.appendRow({...})')
     这里收到的是一段 JSON 字符串，自己 parse
     列宽跟表头一致：来源 80 / 标题 320 / 日期 110 / 摘要 380 / url 260 / 菜单 40
     ====================================================================== */
  window.appendRow = function (jsonStr) {
    var r = {};
    try {
      r = JSON.parse(jsonStr) || {};
    } catch (e) {
      r = { source: '', title: String(jsonStr), date: '未知', summary: '', url: '' };
    }

    var row = document.createElement('div');
    row.className = 'table-row';
    row.dataset.url = (r.url === null || r.url === undefined) ? '' : String(r.url);
    row.dataset.title = (r.title === null || r.title === undefined) ? '' : String(r.title);
    row.dataset.summary = (r.summary === null || r.summary === undefined) ? '' : String(r.summary);
    /* 日期倒序排序用（批 4-A-5）：原始日期文本，缺省「未知」 */
    row.dataset.date = (r.date === null || r.date === undefined || r.date === '') ? '未知' : String(r.date);
    /* 来源页签筛选用：来源中文名（批 4-A-4） */
    row.dataset.source = (r.source === null || r.source === undefined) ? '' : String(r.source);
    /* 导出分组用：书名（批 5-C） */
    row.dataset.book = (r.book === null || r.book === undefined || r.book === '')
      ? '' : String(r.book);
    /* 右键菜单「打开源链接」用：原始关键词 + 引擎 id（批 4-A-3） */
    row.dataset.keyword = (r.keyword === null || r.keyword === undefined) ? '' : String(r.keyword);
    row.dataset.srcId = (r.srcId === null || r.srcId === undefined) ? '' : String(r.srcId);

    /* 已加白名单 → 整行文字灰化（记住是 common 白名单，白名单词清空时不被还原） */
    if (r.is_white) {
      row.classList.add('row-white');
      row.dataset.whiteCommon = '1';
    }

    /* 行首勾选框 */
    var checkCell = document.createElement('div');
    checkCell.className = 'td col-check';
    var check = document.createElement('input');
    check.type = 'checkbox';
    check.className = 'row-check';
    /* 勾选框点击 = Ctrl+点等价（只影响该行，不触发行点击） */
    check.addEventListener('click', function (e) {
      e.stopPropagation();                 // 不让行点击也触发
      row.classList.toggle('row-selected', check.checked);
      var i = getAllRows().indexOf(row);
      if (i >= 0) { _lastAnchorRowIdx = i; }
      syncCheckAllState();
    });
    checkCell.appendChild(check);
    row.appendChild(checkCell);

    row.appendChild(makeCell('来源', 'td col-src', r.source));

    /* 标题格（批 5-D）：新链接 → 加粗 + 前缀【新发现！】 */
    var isNew = !!r.isNew;
    var titleCell = document.createElement('div');
    titleCell.className = 'td col-title';
    var titleText = (r.title === null || r.title === undefined) ? '' : String(r.title);
    if (isNew) { titleText = '【新发现！】' + titleText; }
    titleCell.textContent = titleText;
    titleCell.title = titleText;
    titleCell.setAttribute('data-label', '标题');
    if (isNew) { titleCell.style.fontWeight = 'bold'; }
    row.appendChild(titleCell);

    row.appendChild(makeCell('日期', 'td col-date', r.date));
    row.appendChild(makeCell('摘要', 'td col-abs', r.summary));
    row.appendChild(makeUrlCell(r.url));

    /* 行点击选中：单击单选 / Ctrl 累加 / Shift 区间
       点勾选框、URL、菜单、浮层 → 不触发行选中 */
    row.addEventListener('click', function (e) {
      if (e.target.closest('input[type=checkbox]')) { return; }
      if (e.target.closest('a')) { return; }
      if (e.target.closest('.col-menu')) { return; }
      if (e.target.closest('.row-menu')) { return; }
      if (e.target.closest('.popup') || e.target.closest('#suffixPopup')) { return; }
      handleRowClick(row, e);
    });

    /* 行上右键 → 同一张菜单（批 4-A-3） */
    row.addEventListener('contextmenu', function (e) {
      e.preventDefault();
      _ctxTargetRow = row;
      window.showRowMenu(e.clientX, e.clientY);
    });

    // ★ 智能滚动：在 append 之前先判断"用户是否接近底部"
    //   （append 之后 scrollHeight 会变大，判断会失真）
    var NEAR_BOTTOM_PX = 40;   // 离底部 40px 内算"接近底部"
    var wasAtBottom = true;
    if (tableScroll) {
      var distToBottom = tableScroll.scrollHeight - tableScroll.scrollTop - tableScroll.clientHeight;
      wasAtBottom = distToBottom <= NEAR_BOTTOM_PX;
    }

    tableBody.appendChild(row);

    // 只有用户本来就接近底部，才跟随滚动
    if (tableScroll && wasAtBottom) {
      tableScroll.scrollTop = tableScroll.scrollHeight;
    }

    insertRowInOrder(row);
    applyFilterToRow(row);

    return tableBody.children.length;
  };

  /* 行点击核心：单击单选 / Ctrl 累加 toggle / Shift 区间全选 */
  function handleRowClick(rowEl, e) {
    if (_drag.suppressNextClick) {          // 刚做完框选，这次 click 吞掉
      _drag.suppressNextClick = false;
      return;
    }
    var all = getAllRows();
    var idx = all.indexOf(rowEl);
    if (idx < 0) { return; }

    var isCtrl = e.ctrlKey || e.metaKey;
    var isShift = e.shiftKey;

    if (isShift && _lastAnchorRowIdx !== null) {
      // Shift 区间：从 anchor 到 idx 全勾上（anchor 不动）
      var lo = Math.min(_lastAnchorRowIdx, idx);
      var hi = Math.max(_lastAnchorRowIdx, idx);
      all.forEach(function (r, i) {
        var cb = r.querySelector('input[type=checkbox].row-check');
        var on = (i >= lo && i <= hi);
        if (cb) { cb.checked = on; }
        r.classList.toggle('row-selected', on);
      });
    } else if (isCtrl) {
      // Ctrl 累加：toggle 当前行
      var cb2 = rowEl.querySelector('input[type=checkbox].row-check');
      if (cb2) { cb2.checked = !cb2.checked; }
      rowEl.classList.toggle('row-selected', !!(cb2 && cb2.checked));
      _lastAnchorRowIdx = idx;
    } else {
      // 单击单选：清空其他，只勾当前
      all.forEach(function (r, i) {
        var cb = r.querySelector('input[type=checkbox].row-check');
        var on = (i === idx);
        if (cb) { cb.checked = on; }
        r.classList.toggle('row-selected', on);
      });
      _lastAnchorRowIdx = idx;
    }

    syncCheckAllState();
  }

  /* ======================================================================
     框选（批 4-A-2）
     - 在 .table-scroll 上按下左键 → 拖动超 6px 进入框选 → 画半透明蓝框
     - 松手时框覆盖到的行全部选中（绿底 + 勾选框）
     - 触到表格上/下边缘 → 自动滚动（用定时器，鼠标停在边缘不动也会继续滚）
     - 框选结束吞掉随之而来的 click，避免又变成单选
     ====================================================================== */
  function dragBoxEl() { return document.getElementById('dragBox'); }

  function stopAutoScroll() {
    if (_drag.autoScrollTimer) {
      clearInterval(_drag.autoScrollTimer);
      _drag.autoScrollTimer = null;
    }
    _drag.autoScrollDir = 0;
  }

  function updateAutoScroll(clientY) {
    if (!tableScroll) { return; }
    var rect = tableScroll.getBoundingClientRect();
    var EDGE = 30;
    var dir = 0;
    if (clientY < rect.top + EDGE) { dir = -1; }
    else if (clientY > rect.bottom - EDGE) { dir = 1; }

    if (dir === _drag.autoScrollDir) { return; }   // 方向没变，定时器保持原样

    stopAutoScroll();
    _drag.autoScrollDir = dir;
    if (dir !== 0) {
      _drag.autoScrollTimer = setInterval(function () {
        if (!_drag.active) { stopAutoScroll(); return; }
        tableScroll.scrollTop += dir * 8;
      }, 16);
    }
  }

  /* 框选期间吞掉 click（冒泡阶段之前的捕获阶段） */
  function dragSwallowClick(ev) {
    if (!_drag.suppressNextClick) { return; }
    _drag.suppressNextClick = false;
    ev.stopPropagation();
    ev.preventDefault();
    document.removeEventListener('click', dragSwallowClick, true);
  }

  function onDragMove(e) {
    _drag.curX = e.clientX;
    _drag.curY = e.clientY;

    var dx = Math.abs(_drag.curX - _drag.startX);
    var dy = Math.abs(_drag.curY - _drag.startY);
    if (!_drag.active && dx < DRAG_THRESHOLD && dy < DRAG_THRESHOLD) { return; }

    _drag.active = true;
    document.body.classList.add('dragging');

    var box = dragBoxEl();
    if (box) {
      box.style.display = 'block';
      box.style.left = Math.min(_drag.startX, _drag.curX) + 'px';
      box.style.top = Math.min(_drag.startY, _drag.curY) + 'px';
      box.style.width = Math.abs(_drag.curX - _drag.startX) + 'px';
      box.style.height = Math.abs(_drag.curY - _drag.startY) + 'px';
    }

    updateAutoScroll(e.clientY);
  }

  function onDragUp() {
    document.removeEventListener('mousemove', onDragMove);
    document.removeEventListener('mouseup', onDragUp);
    stopAutoScroll();
    document.body.classList.remove('dragging');

    var box = dragBoxEl();
    if (box) { box.style.display = 'none'; }

    if (!_drag.active) {
      // 没进框选模式 → 当普通点击处理，不干预
      document.removeEventListener('click', dragSwallowClick, true);
      return;
    }

    _drag.active = false;

    // 框选结束：吞掉接下来这次 click（只吞一次）
    _drag.suppressNextClick = true;
    setTimeout(function () { _drag.suppressNextClick = false; }, 80);

    // 计算框的矩形
    var boxLeft = Math.min(_drag.startX, _drag.curX);
    var boxRight = Math.max(_drag.startX, _drag.curX);
    var boxTop = Math.min(_drag.startY, _drag.curY);
    var boxBottom = Math.max(_drag.startY, _drag.curY);

    var rows = getAllRows();
    var selectedCount = 0;
    var lastIdx = -1;

    rows.forEach(function (r, i) {
      var rect = r.getBoundingClientRect();
      var yOverlap = !(rect.bottom < boxTop || rect.top > boxBottom);
      var xOverlap = !(boxRight < rect.left || boxLeft > rect.right);
      if (yOverlap && xOverlap) {
        var cb = r.querySelector('input[type=checkbox].row-check');
        if (cb) { cb.checked = true; }
        r.classList.add('row-selected');
        selectedCount++;
        lastIdx = i;
      }
    });

    // anchor 指向框选里的最后一行，方便之后 Shift 继续扩
    if (selectedCount > 0 && lastIdx >= 0) { _lastAnchorRowIdx = lastIdx; }

    syncCheckAllState();
  }

  /* 表格滚动区按下左键 → 准备框选 */
  if (tableScroll) {
    tableScroll.addEventListener('mousedown', function (e) {
      if (e.button !== 0) { return; }                              // 只处理左键
      if (e.target.closest('input[type=checkbox]')) { return; }    // 勾选框
      if (e.target.closest('a')) { return; }                       // URL 链接
      if (e.target.closest('.col-menu')) { return; }               // ⋯ 菜单
      if (e.target.closest('.row-menu')) { return; }
      if (e.target.closest('.mask')) { return; }                   // 弹窗遮罩
      if (e.target.closest('#suffixPopup')) { return; }            // 后缀浮层

      _drag.active = false;
      _drag.startX = e.clientX;
      _drag.startY = e.clientY;
      _drag.curX = e.clientX;
      _drag.curY = e.clientY;

      document.addEventListener('mousemove', onDragMove);
      document.addEventListener('mouseup', onDragUp);
      document.addEventListener('click', dragSwallowClick, true);
    });
  }

  /* ======================================================================
     行右键 / ⋯ 菜单（批 4-A-3）
     - 动作作用于「所有选中行」；没有选中行时只作用于右键/⋯ 的那一行
     ====================================================================== */
  window.showRowMenu = function (x, y) {
    var menu = document.getElementById('rowContextMenu');
    if (!menu) { return; }
    menu.innerHTML =
      '<div class="row-menu-item" data-act="copy">复制链接</div>' +
      '<div class="row-menu-item" data-act="open">打开链接</div>' +
      '<div class="row-menu-item" data-act="open-src">打开源链接</div>' +
      '<div class="row-menu-sep"></div>' +
      '<div class="row-menu-item" data-act="white">加入白名单</div>' +
      '<div class="row-menu-item danger" data-act="unwhite">取消白名单</div>';

    /* 先亮出来量真实尺寸，若超出屏幕右/下边缘再往回收 */
    menu.style.display = 'block';
    menu.style.visibility = 'hidden';
    menu.style.left = '0px';
    menu.style.top = '0px';

    var menuW = menu.offsetWidth || 180;
    var menuH = menu.offsetHeight || 220;
    var vw = window.innerWidth;
    var vh = window.innerHeight;
    if (x + menuW > vw) { x = vw - menuW - 4; }
    if (y + menuH > vh) { y = vh - menuH - 4; }
    if (x < 0) { x = 4; }
    if (y < 0) { y = 4; }

    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    menu.style.visibility = 'visible';

    menu.onclick = function (ev) {
      var item = ev.target.closest('.row-menu-item');
      if (!item) { return; }
      var act = item.dataset.act;
      menu.style.display = 'none';
      window.doRowAction(act);
    };
  };

  /* 点别处 / Esc 关闭菜单 */
  document.addEventListener('click', function (e) {
    var menu = document.getElementById('rowContextMenu');
    if (menu && menu.style.display === 'block' && !menu.contains(e.target)) {
      menu.style.display = 'none';
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      var menu = document.getElementById('rowContextMenu');
      if (menu) { menu.style.display = 'none'; }
    }
  });

  /* 取每行的数据（url / 关键词 / 引擎 id） */
  function getDataset(element) {
    return element && element.dataset ? element.dataset : {};
  }

  function collectRowItems(rows) {
    return rows.map(function (r) {
      var data = getDataset(r);
      return {
        url: (data.url || '').trim(),
        keyword: (data.keyword || '').trim(),
        srcId: (data.srcId || '').trim()
      };
    });
  }

  /* 「复制链接」：剪贴板写入，失败回退 textarea + execCommand */
  function actCopyUrls(urls) {
    if (urls.length === 0) { window.appendLog('[提示] 没有可复制的链接'); return; }
    var text = urls.join('\n');
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        logCount('已复制', urls.length);
      }, function () {
        window.appendLog('[错误] 复制失败（剪贴板被拒绝）');
      });
    } else {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch (err) { /* 忽略 */ }
      document.body.removeChild(ta);
      logCount('已复制', urls.length);
    }
  }

  /* 菜单动作总入口：act ∈ copy / open / open-src / white / unwhite */
  window.doRowAction = function (act) {
    var rows = getActionRows();
    if (rows.length === 0) { return; }
    var items = collectRowItems(rows);
    var urls = collectUrls(items);

    if (act === 'copy') {
      actCopyUrls(urls);

    } else if (act === 'open') {
      if (urls.length === 0) { window.appendLog('[提示] 没有可打开的链接'); return; }
      if (!requireApi()) { return; }
      urls.forEach(function (u) { window.pywebview.api.open_url(u); });
      logCount('已打开', urls.length);

    } else if (act === 'open-src') {
      if (!requireApi()) { return; }
      var cnt = 0;
      items.forEach(function (it) {
        if (!it.keyword) { return; }
        if (it.srcId === 'quark_cn') {
          window.pywebview.api.open_manual_quark_search(
            it.srcId,
            encodeURIComponent(it.keyword)
          );
        } else {
          var base = ENGINE_URL[it.srcId] || ENGINE_URL['baidu'];
          window.pywebview.api.open_url(base + encodeURIComponent(it.keyword));
        }
        cnt++;
      });
      if (cnt === 0) { window.appendLog('[提示] 这些行没有关键词信息'); }
      else { window.appendLog('已打开 ' + cnt + ' 个源链接'); }

    } else if (act === 'white') {
      if (urls.length === 0) { window.appendLog('[提示] 没有可加入白名单的链接'); return; }
      if (!requireApi()) { return; }
      window.pywebview.api.add_to_whitelist(urls).then(function () {
        rows.forEach(function (r) {
          r.classList.add('row-white');
          r.dataset.whiteCommon = '1';
          var cb = r.querySelector('input[type=checkbox].row-check');
          if (cb) { cb.checked = false; }
          r.classList.remove('row-selected');
        });
        window.reorderRows();
        syncCheckAllState();
        logCount('已加入白名单', urls.length);
      });

    } else if (act === 'unwhite') {
      if (urls.length === 0) { window.appendLog('[提示] 没有可取消白名单的链接'); return; }
      if (!requireApi()) { return; }
      window.pywebview.api.remove_from_whitelist(urls).then(function () {
        rows.forEach(function (r) {
          r.classList.remove('row-white');
          delete r.dataset.whiteCommon;
        });
        window.reorderRows();
        logCount('已取消白名单', urls.length);
      });
    }
  };

  /* 日期 → 可比较的 YYYY-MM-DD 键（"未知"/解析不出 → '' 排最后） */
  function parseDateKey(dateStr) {
    var s = String(dateStr === null || dateStr === undefined ? '' : dateStr).trim();
    if (!s || s === '未知') { return ''; }
    s = s.replace(/年|月/g, '-').replace(/日/g, '');
    s = s.replace(/\//g, '-').replace(/\./g, '-');
    s = s.replace(/\s+/g, '');
    var m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
    if (m) {
      return m[1] + '-' + ('0' + m[2]).slice(-2) + '-' + ('0' + m[3]).slice(-2);
    }
    return '';
  }

  function compareRowsByDisplayOrder(a, b) {
    if (!a || !b) { return a ? -1 : (b ? 1 : 0); }
    var aWhite = !!(a.classList && a.classList.contains('row-white'));
    var bWhite = !!(b.classList && b.classList.contains('row-white'));
    if (aWhite !== bWhite) { return aWhite ? 1 : -1; }

    var da = parseDateKey(getDataset(a).date || '');
    var db = parseDateKey(getDataset(b).date || '');
    if (!da && !db) { return 0; }
    if (!da) { return 1; }
    if (!db) { return -1; }
    return db.localeCompare(da);
  }

  function insertRowInOrder(row) {
    var tbody = document.getElementById('tableBody');
    if (!tbody || tbody.children.length < 2) { return; }

    var rowIndex = tbody.children.length - 1;
    var low = 0;
    var high = rowIndex;
    while (low < high) {
      var mid = Math.floor((low + high) / 2);
      if (compareRowsByDisplayOrder(tbody.children[mid], row) <= 0) {
        low = mid + 1;
      } else {
        high = mid;
      }
    }

    if (low < rowIndex) {
      tbody.insertBefore(row, tbody.children[low]);
      _lastAnchorRowIdx = null;
    }
  }

  /* 白名单行沉底 + 组内日期倒序（新→旧，"未知"排最后）
     沉底优先级 > 日期排序：先按白名单分两组，再各自按日期倒序 */
  window.reorderRows = function () {
    var tbody = document.getElementById('tableBody');
    if (!tbody) { return; }
    var allRows = getAllRows();
    if (allRows.length === 0) { return; }

    var normalRows = [];
    var whiteRows = [];
    allRows.forEach(function (r) {
      if (r.classList && r.classList.contains('row-white')) { whiteRows.push(r); }
      else { normalRows.push(r); }
    });

    function sortByDateDesc(rows) {
      rows.sort(function (a, b) {
        var da = parseDateKey(getDataset(a).date || '');
        var db = parseDateKey(getDataset(b).date || '');
        if (!da && !db) { return 0; }
        if (!da) { return 1; }      // a 无日期 → 排后面
        if (!db) { return -1; }     // b 无日期 → 排后面
        return db.localeCompare(da);   // 倒序
      });
    }
    sortByDateDesc(normalRows);
    sortByDateDesc(whiteRows);

    var desired = normalRows.concat(whiteRows);
    var current = Array.prototype.slice.call(tbody.children);
    var changed = desired.length !== current.length ||
      desired.some(function (row, i) { return current[i] !== row; });
    if (!changed) { return; }

    tbody.innerHTML = '';
    desired.forEach(function (r) { tbody.appendChild(r); });

    _lastAnchorRowIdx = null;   // DOM 顺序变了 → 旧的 anchor 序号失效
  };

  /* ======================================================================
     筛选（批 4-A-4）：来源页签 + 工具栏搜索框，两者可叠加
     - tabOK：当前页签是「全部」或该行来源与页签一致
     - textOK：搜索框为空，或 标题/摘要/url 任一包含关键词
     - 两个都满足才显示；最后 reorderRows 保证白名单行始终沉底
     ====================================================================== */
  /* 页签分组：点一个页签 = 匹配多个来源（PC + 移动版归到一组） */
  var TAB_GROUPS = {
    '百度':   ['百度', '百度移动版'],
    '知道':   ['知道', '知道移动版'],
    '头条':   ['头条', '头条移动版'],
    '搜狗':   ['搜狗', '搜狗移动版'],
    '360':    ['360', '360移动版'],
  };

  function applyFilterToRow(r) {
    if (!r) { return; }
    var data = getDataset(r);
    var src = data.source || '';
    var allowedSrcs = TAB_GROUPS[_currentTabFilter] || [_currentTabFilter];
    var tabOK = (_currentTabFilter === TAB_ALL) || (allowedSrcs.indexOf(src) >= 0);

    var textOK = true;
    if (_searchBoxFilter) {
      var hay = (
        (data.title || '') + ' ' +
        (data.summary || '') + ' ' +
        (data.url || '')
      ).toLowerCase();
      textOK = hay.indexOf(_searchBoxFilter) >= 0;
    }

    r.style.display = (tabOK && textOK) ? '' : 'none';
  }

  window.applyFilters = function () {
    var allRows = getAllRows();
    allRows.forEach(applyFilterToRow);

    if (typeof window.reorderRows === 'function') { window.reorderRows(); }
  };

  /* 来源页签点击：切换 _currentTabFilter + 高亮 */
  (function bindTabs() {
    var tabsBox = document.getElementById('tabs');
    if (!tabsBox) { return; }
    var tabs = tabsBox.querySelectorAll('.tab');
    Array.prototype.forEach.call(tabs, function (tab) {
      tab.addEventListener('click', function () {
        _currentTabFilter = (tab.textContent || '').trim();
        Array.prototype.forEach.call(tabs, function (t) {
          t.classList.toggle('active', t === tab);
        });
        window.applyFilters();
      });
    });
  })();

  /* 工具栏搜索框：实时过滤 + 「清空」恢复全显 */
  if (tableSearchInput) {
    tableSearchInput.addEventListener('input', function () {
      _searchBoxFilter = (tableSearchInput.value || '').trim().toLowerCase();
      window.applyFilters();
    });
  }

  if (btnTbSearchClear) {
    btnTbSearchClear.addEventListener('click', function () {
      if (tableSearchInput) { tableSearchInput.value = ''; }
      _searchBoxFilter = '';
      window.applyFilters();
    });
  }

  /* 普通单元格：整格 ellipsis 截断，鼠标悬停看全文 */
  function makeCell(label, cls, value) {
    var cell = document.createElement('div');
    cell.className = cls;
    var text = (value === null || value === undefined) ? '' : String(value);
    cell.textContent = text;
    cell.title = text;                       // 悬停显示完整内容
    cell.setAttribute('data-label', label);
    return cell;
  }

  /* url 单元格：蓝色可点链接（空白 / 非 http 就按纯文本显示）
     ★ 点击走 Python 的 webbrowser.open，不让 WebView 内部跳转：
       href 用 javascript:void(0)（不真实导航），真正的打开动作在 click 监听里。
       用 addEventListener 而不是内联 onclick，是因为 url 里可能带单引号，
       拼字符串会直接把属性拼坏。 */
  function makeUrlCell(url) {
    var cell = document.createElement('div');
    cell.className = 'td col-url';
    var text = (url === null || url === undefined) ? '' : String(url);
    cell.title = text;

    if (/^https?:\/\//i.test(text)) {
      var a = document.createElement('a');
      a.className = 'row-link';
      a.href = 'javascript:void(0)';
      a.textContent = text;
      a.addEventListener('click', function () {
        if (apiReady()) { window.pywebview.api.open_url(text); }
      });
      cell.appendChild(a);
    } else {
      cell.textContent = text;
    }
    return cell;
  }

  function apiReady() {
    return !!(window.pywebview && window.pywebview.api);
  }

  /* 调后端前的统一守卫：就绪返回 true，否则记一条错误日志并返回 false */
  function requireApi() {
    if (!apiReady()) {
      window.appendLog('[错误] pywebview.api 还没就绪');
      return false;
    }
    return true;
  }

  /* 统一的「N 个链接」日志 */
  function logCount(prefix, n) {
    window.appendLog(prefix + ' ' + n + ' 个链接');
  }

  /* 从 DOM 行（tr）或 {url:...} 对象里取出非空 url 数组 */
  function collectUrls(items) {
    return items.map(function (it) {
      var raw = (it.url !== undefined && it.url !== null) ? it.url
        : (it.dataset ? it.dataset.url : '');
      return String(raw || '').trim();
    }).filter(function (u) { return !!u; });
  }

  /* ==================== 搜索中状态切换 ==================== */
  /* Python 侧搜完/开跑时会调 window.setSearching(true/false) */
  window.setSearching = function (isSearching) {
    var on = !!isSearching;

    // 搜索按钮：搜索中 → 灰掉禁用
    btnSearch.disabled = on;
    btnSearch.classList.toggle('btn-primary', !on);
    btnSearch.classList.toggle('btn-disabled', on);

    // 停止按钮：搜索中 → 亮红可点
    btnSearchStop.disabled = !on;
    btnSearchStop.classList.toggle('btn-disabled', !on);
    btnSearchStop.classList.toggle('btn-danger', on);

    return on;
  };

  /* ==================== 读取界面输入 ==================== */
  function getCheckedSources() {
    var boxes = document.querySelectorAll('input[name="source"]:checked');
    return Array.prototype.slice.call(boxes).map(function (el) { return el.value; });
  }

  function getPagesArg() {
    var raw = (pagesInput.value || '').trim();
    if (raw === '') { return 'auto'; }                       // 留空 = 自动
    if (/^\d+$/.test(raw)) { return parseInt(raw, 10); }     // 纯数字 → int
    return raw;                                              // 其他原样交给后端
  }

  /* ==================== 搜索 / 停止 ==================== */
  /* 单个搜索（双击书签用，绕开选中逻辑，不动输入框） */
  window.searchOneBook = function (name) {
    var book = (name === null || name === undefined) ? '' : String(name).trim();
    if (!book) { window.appendLog('[提示] 书名为空'); return; }

    var sources = getCheckedSources();
    if (!sources.length) { window.appendLog('[提示] 请至少勾选一个来源'); return; }
    if (!requireApi()) { return; }

    var pages = getPagesArg();
    window.pywebview.api.start_search([{ book: book, keyword: book }], sources, pages)
      .then(function (res) {
        if (res === 'already_running') {
          window.appendLog('[提示] 上一次搜索还在跑，请稍候');
        } else if (res === 'invalid') {
          window.appendLog('[提示] 搜索参数不合法');
        }
      });
  };

  /* 统一起点（「搜索」按钮）：有选中书签 → 批量搜书签；没选中 → 搜输入框 */
  window.doSearch = function () {
    var selectedIds = (window._selectedBookmarkIds instanceof Set)
      ? window._selectedBookmarkIds : new Set();

    var sources = getCheckedSources();
    if (!sources.length) { window.appendLog('[提示] 请至少勾选一个来源'); return; }
    if (!requireApi()) { return; }

    var pages = getPagesArg();

    function run(tasks) {
      window.pywebview.api.start_search(tasks, sources, pages).then(function (res) {
        if (res === 'already_running') {
          window.appendLog('[提示] 上一次搜索还在跑，请稍候');
        } else if (res === 'invalid') {
          window.appendLog('[提示] 搜索参数不合法');
        }
      });
    }

    if (selectedIds.size > 0) {
      // 有选中书签 → 拉书签数据 → 按启用后缀展开 tasks
      window.pywebview.api.get_bookmarks().then(function (books) {
        var tasks = [];
        (books || []).forEach(function (b) {
          if (!selectedIds.has(b.id)) { return; }
          var enabled = (b.suffixes || []).filter(function (s) {
            return s.enabled !== false;
          });
          if (enabled.length === 0) {
            tasks.push({ book: b.name, keyword: b.name });
          } else {
            enabled.forEach(function (s) {
              tasks.push({ book: b.name, keyword: b.name + (s.text || '') });
            });
          }
        });
        if (!tasks.length) {
          window.appendLog('[提示] 选中的书签没有可用的搜索词');
          return;
        }
        run(tasks);
      });
    } else {
      // 没选中 → 用输入框
      var name = (bookInput.value || '').trim();
      if (!name) { window.appendLog('[提示] 请先输入书名，或选中书签'); return; }
      run([{ book: name, keyword: name }]);
    }
  };

  /* 「搜索」按钮：有选中批量搜书签，没选中搜输入框 */
  btnSearch.addEventListener('click', function () {
    window.doSearch();
  });

  btnSearchStop.addEventListener('click', function () {
    window.appendLog('收到停止指令');
    // 不在这里 setSearching(false)：等后台线程真的退出后，由 Python 的
    // finally 统一调 setSearching(false)，否则按钮先恢复但线程还在跑，
    // 用户会以为已经停了。
    if (apiReady()) { window.pywebview.api.stop_search(); }
  });

  /* ==================== 清空列表 ==================== */
  /* 前端清表格，同时通知后端清去重集合（否则再搜同一个词，旧 URL 不会重现） */
  if (btnTbClear) {
    btnTbClear.addEventListener('click', function () {
      tableBody.innerHTML = '';
      _lastAnchorRowIdx = null;               // 列表清空 → 重置 Shift 锚点
      if (apiReady()) { window.pywebview.api.clear_displayed_urls(); }
      window.appendLog('列表已清空');
    });
  }

  /* ==================== 导出结果（批 5-C） ==================== */
  /* 只导出「当前筛选下可见」的行：页签 / 搜索框过滤掉的行不导出 */
  var btnTbExport = document.getElementById('btnTbExport');
  if (btnTbExport) {
    btnTbExport.addEventListener('click', function () {
      var rows = [];
      Array.prototype.forEach.call(
        tableBody.querySelectorAll('.table-row'),
        function (r) {
          if (!r || r.style.display === 'none') { return; }   // 被筛掉的不导出
          var data = getDataset(r);
          var url = (data.url || '').trim();
          if (!url) { return; }
          rows.push({
            book: data.book || '',
            source: data.source || '',
            url: url,
          });
        }
      );
      if (rows.length === 0) {
        window.appendLog('当前没有可导出的内容');
        return;
      }
      if (!requireApi()) { return; }
      window.pywebview.api.export_results(rows).then(function (res) {
        if (res === 'empty') { window.appendLog('当前没有可导出的内容'); }
      });
    });
  }

  /* ==================== 重置历史记录（批 5-D） ==================== */
  var btnTbClearSeen = document.getElementById('btnTbClearSeen');
  if (btnTbClearSeen) {
    btnTbClearSeen.addEventListener('click', function () {
      /* confirm 在个别 WebView 后端可能不可用 → 抛错时按「确认」继续 */
      var ok = true;
      try {
        ok = window.confirm('重置历史记录？\n重置后，以前搜过的 URL 会重新标记为【新发现！】。');
      } catch (e) {
        ok = true;
      }
      if (ok === false) { return; }
      if (!requireApi()) { return; }
      window.pywebview.api.clear_seen_urls();
    });
  }

  /* ==================== 批量打开 / 批量复制 / 载入历史（批 6） ==================== */
  /* 三个按钮原先都没有点击逻辑，这里补齐；选中行集合复用 getActionRows() */
  var btnTbOpen = document.getElementById('btnTbOpen');
  var btnTbCopy = document.getElementById('btnTbCopy');
  var btnTbHistory = document.getElementById('btnTbHistory');

  /* 「批量打开」：打开勾选/选中行的 URL（走 Python webbrowser.open） */
  if (btnTbOpen) {
    btnTbOpen.addEventListener('click', function () {
      var rows = getActionRows();
      if (rows.length === 0) {
        window.appendLog('没有选中任何行');
        return;
      }
      var urls = collectUrls(rows);
      if (urls.length === 0) {
        window.appendLog('选中的行没有链接');
        return;
      }
      if (!requireApi()) { return; }
      urls.forEach(function (u) { window.pywebview.api.open_url(u); });
      logCount('已打开', urls.length);
    });
  }

  /* 「批量复制」：把勾选/选中行的 URL 按行拼起来写剪贴板 */
  if (btnTbCopy) {
    btnTbCopy.addEventListener('click', function () {
      var rows = getActionRows();
      var urls = collectUrls(rows);
      if (urls.length === 0) {
        window.appendLog('没有选中任何行');
        return;
      }
      actCopyUrls(urls);          // 已含剪贴板 + textarea 回退（L1193）
    });
  }

  /* 「载入历史数据」：读 seen_urls.json，逐条追加到表格（不清空已有结果） */
  if (btnTbHistory) {
    btnTbHistory.addEventListener('click', function () {
      if (!requireApi()) { return; }
      window.pywebview.api.load_history().then(function (records) {
        if (!records || records.length === 0) {
          window.appendLog('历史记录为空');
          return;
        }
        records.forEach(function (rec) {
          window.appendRow(JSON.stringify({
            source: rec.source || '历史',
            title: rec.book || '(无书名)',
            date: '',
            summary: '',
            url: rec.url,
            keyword: '',
            srcId: '',
            book: rec.book || '',
            isNew: false,
            is_white: !!rec.is_white,
          }));
        });
        window.appendLog('已载入历史数据 ' + records.length + ' 条');
      });
    });
  }

  /* ==================== 清 cookies ==================== */
  var btnClearCookies = document.getElementById('btnClearCookies');
  if (btnClearCookies) {
    btnClearCookies.addEventListener('click', function () {
      /* confirm 在个别 WebView 后端可能不可用 → 抛错时按「确认」继续 */
      var ok = true;
      try {
        ok = window.confirm('清除 cookies？\n将删除 baidu_engine_data 目录（含登录态）。\n建议先停止正在进行的搜索。');
      } catch (e) {
        ok = true;
      }
      if (ok === false) { return; }
      if (!requireApi()) { return; }
      window.pywebview.api.clear_cookies();
    });
  }

  /* ==================== 行勾选 / 白名单 ==================== */
  function allRows() {
    return Array.prototype.slice.call(tableBody.children);
  }

  function checkedRows() {
    return allRows().filter(function (row) {
      var c = row.querySelector('.row-check');
      return c && c.checked;
    });
  }

  function syncCheckAllState() {
    if (!checkAllRow) { return; }
    var rows = allRows();
    var checked = checkedRows().length;
    checkAllRow.checked = rows.length > 0 && checked === rows.length;
    checkAllRow.indeterminate = checked > 0 && checked < rows.length;
  }

  function setAllRows(checked) {
    allRows().forEach(function (row) {
      var c = row.querySelector('.row-check');
      if (c) { c.checked = checked; }
      row.classList.toggle('row-selected', !!checked);   // 行绿底跟勾选同步
    });
    syncCheckAllState();
  }

  /* 表头全选框：勾了 → 所有行都勾，取消 → 所有行都取消 */
  if (checkAllRow) {
    checkAllRow.addEventListener('change', function () {
      setAllRows(!!checkAllRow.checked);
    });
  }

  /* 工具栏「全选/取消」按钮：切换全部 */
  if (btnTbSelectAll) {
    btnTbSelectAll.addEventListener('click', function () {
      var rows = allRows();
      var allChecked = rows.length > 0 && checkedRows().length === rows.length;
      setAllRows(!allChecked);
    });
  }

  /* 来源行「全选 / 取消」按钮：任意一个没勾 → 全勾；全勾了 → 全不勾 */
  var btnToggleSources = document.getElementById('btnToggleSources');
  if (btnToggleSources) {
    btnToggleSources.addEventListener('click', function () {
      var cbs = document.querySelectorAll('input[name=source]');
      if (cbs.length === 0) { return; }
      var anyOff = false;
      cbs.forEach(function (cb) { if (!cb.checked) { anyOff = true; } });
      cbs.forEach(function (cb) { cb.checked = anyOff; });
    });
  }

  /* 行内勾选变化时同步表头全选框状态 */
  if (tableBody) {
    tableBody.addEventListener('change', function (e) {
      if (e.target && e.target.classList && e.target.classList.contains('row-check')) {
        syncCheckAllState();
      }
    });
  }

  /* 「加白名单」：把勾选行的 URL 加入白名单并落盘，然后给这些行灰化 */
  if (btnTbWhite) {
    btnTbWhite.addEventListener('click', function () {
      var rows = checkedRows();
      var urls = collectUrls(rows);

      if (!urls.length) { window.appendLog('[提示] 请先勾选要加白名单的行'); return; }
      if (!requireApi()) { return; }

      window.pywebview.api.add_to_whitelist(urls).then(function () {
        rows.forEach(function (row) {
          row.classList.add('row-white');
          row.dataset.whiteCommon = '1';
        });
        window.reorderRows();
      });
    });
  }

  /* 「重置白名单」：确认后清空并落盘，移除所有灰化标记 */
  if (btnTbResetWhite) {
    btnTbResetWhite.addEventListener('click', function () {
      /* confirm 在个别 WebView 后端可能不可用 → 抛错时按「确认」继续 */
      var ok = true;
      try {
        ok = window.confirm('重置白名单？\n将清空全部已加白的 URL（不可恢复）。');
      } catch (e) {
        ok = true;
      }
      if (ok === false) { return; }
      if (!requireApi()) { return; }

      window.pywebview.api.clear_whitelist().then(function () {
        allRows().forEach(function (row) {
          row.classList.remove('row-white');
          delete row.dataset.whiteCommon;
        });
        window.reorderRows();
      });
    });
  }

  /* ==================== 白名单词弹窗 ==================== */
  var btnTbWhiteWords = document.getElementById('btnTbWhiteWords');
  var wlWordsDialog = document.getElementById('wlWordsDialog');
  var wlWordsInput = document.getElementById('wlWordsInput');
  var btnWlWordsCancel = document.getElementById('btnWlWordsCancel');
  var btnWlWordsSave = document.getElementById('btnWlWordsSave');

  /* 打开弹窗：拉取现有白名单词，按行填进 textarea */
  if (btnTbWhiteWords) {
    btnTbWhiteWords.addEventListener('click', function () {
      if (!requireApi()) { return; }
      window.pywebview.api.get_whitelist_words().then(function (words) {
        wlWordsInput.value = (words || []).join('\n');
        wlWordsDialog.classList.add('show');
      });
    });
  }

  if (btnWlWordsCancel) {
    btnWlWordsCancel.addEventListener('click', function () {
      wlWordsDialog.classList.remove('show');
    });
  }

  /* 保存：按行拆分 → 全量替换 → Python 侧会自动调 applyWhitelistWords 刷新 */
  if (btnWlWordsSave) {
    btnWlWordsSave.addEventListener('click', function () {
      if (!requireApi()) { return; }
      var words = (wlWordsInput.value || '').split(/\r?\n/)
        .map(function (s) { return s.trim(); })
        .filter(function (s) { return !!s; });
      window.pywebview.api.save_whitelist_words(words).then(function () {
        wlWordsDialog.classList.remove('show');
      });
    });
  }

  /* 重新应用白名单词到所有已抓行（Python 保存后调用）：
     命中 → 灰化并标记 wlWord；不再命中且只是词灰化的 → 还原 */
  window.applyWhitelistWords = function () {
    if (!apiReady()) { return; }
    var tasks = [];
    allRows().forEach(function (row) {
      if (!row) { return; }
      var data = getDataset(row);
      var text = (data.title || '') + ' ' +
                 (data.summary || '') + ' ' +
                 (data.url || '');
      tasks.push(window.pywebview.api.check_whitelist_word(text).then(function (hit) {
        if (hit) {
          row.classList.add('row-white');
          data.wlWord = '1';
        } else if (data.wlWord === '1') {
          delete data.wlWord;
          if (data.whiteCommon !== '1') {
            row.classList.remove('row-white');
          }
        }
      }));
    });
    Promise.all(tasks).then(function () { window.reorderRows(); });
  };

  /* ==================== 验证码弹窗 ==================== */
  /* Python 调：window.showCaptchaDialog('搜狗风控（HTTP 403）…') */
  var captchaDialog = document.getElementById('captchaDialog');
  var captchaText = document.getElementById('captchaText');
  var btnCaptchaOk = document.getElementById('btnCaptchaOk');
  var btnCaptchaStop = document.getElementById('btnCaptchaStop');
  var btnCaptchaContinueTop = document.getElementById('btnCaptchaContinue');

  function hideCaptchaDialog() {
    captchaDialog.classList.remove('show');
  }

  window.showCaptchaDialog = function (reason) {
    var text = (reason === null || reason === undefined) ? '' : String(reason);
    captchaText.textContent = text;
    captchaDialog.classList.add('show');
    try { window.focus(); } catch (e) { /* 某些环境下会抛，忽略 */ }
    return true;
  };

  /* 「我已过验证，继续」：通知 Python 唤醒暂停中的线程，并收起弹窗 */
  function onCaptchaContinue() {
    if (apiReady()) { window.pywebview.api.captcha_continue(); }
    hideCaptchaDialog();
  }

  /* 「停止本轮」：跟顶栏「停止」同一个动作（顺带把卡在等验证的线程唤醒） */
  function onCaptchaStop() {
    window.appendLog('收到停止指令');
    if (apiReady()) { window.pywebview.api.stop_search(); }
    hideCaptchaDialog();
  }

  btnCaptchaOk.addEventListener('click', onCaptchaContinue);
  btnCaptchaStop.addEventListener('click', onCaptchaStop);
  /* 顶栏那条「我已过验证，继续」= 弹窗里的继续按钮 */
  btnCaptchaContinueTop.addEventListener('click', onCaptchaContinue);

  /* ==================== 前台开关 ==================== */
  var switchFrontend = document.getElementById('switchFrontend');

  switchFrontend.addEventListener('change', function () {
    var on = !!switchFrontend.checked;
    if (apiReady()) { window.pywebview.api.set_frontend_mode(on); }
  });

  /* ==================== 书签（批 3-A） ==================== */
  var bookmarkRow = document.getElementById('bookmarkRow');
  var btnBookmark = document.getElementById('btnBookmark');

  /* 选中集合：存书签 id（用 Set，所以允许重名书签各自独立选中） */
  function bmSelectedIds() {
    if (!(window._selectedBookmarkIds instanceof Set)) {
      window._selectedBookmarkIds = new Set();
    }
    return window._selectedBookmarkIds;
  }

  function loadBookmarks() {
    if (!apiReady()) { return; }
    window.pywebview.api.get_bookmarks().then(function (books) {
      window.renderBookmarks(JSON.stringify(books || []));
    });
  }

  /* Python 调：window.renderBookmarks('<json 字符串>') */
  window.renderBookmarks = function (booksJsonStr) {
    var books;
    try { books = JSON.parse(booksJsonStr || '[]'); }
    catch (e) { books = []; }
    if (!bookmarkRow) { return; }

    var selectedIds = bmSelectedIds();
    bookmarkRow.innerHTML = '';

    books.forEach(function (b) {
      var chip = document.createElement('div');
      chip.className = 'bm-chip' + (selectedIds.has(b.id) ? ' selected' : '');
      chip.dataset.bmId = b.id;
      chip.dataset.bmName = b.name;

      var nameEl = document.createElement('span');
      nameEl.textContent = b.name;

      var countEl = document.createElement('span');
      countEl.className = 'bm-count';
      countEl.textContent = b.suffixCount;

      var arrowEl = document.createElement('span');
      arrowEl.className = 'bm-arrow';
      arrowEl.textContent = '▼';
      arrowEl.dataset.action = 'expand';
      // 点箭头：打开后缀浮层（下批 3-B）
      arrowEl.addEventListener('click', function (e) {
        e.stopPropagation();
        window.openSuffixPopup(b.id, chip);
      });

      chip.appendChild(nameEl);
      chip.appendChild(document.createTextNode(' '));
      chip.appendChild(countEl);
      chip.appendChild(arrowEl);

      // 单击 / 双击冲突处理：双击时取消单击的选中切换
      var clickTimer = null;

      // 左键单击：仅切换选中
      chip.addEventListener('click', function () {
        if (clickTimer) {
          clearTimeout(clickTimer);
          clickTimer = null;
          return;
        }
        clickTimer = setTimeout(function () {
          clickTimer = null;
          if (selectedIds.has(b.id)) { selectedIds.delete(b.id); }
          else { selectedIds.add(b.id); }
          window._selectedBookmarkIds = selectedIds;
          chip.classList.toggle('selected');
        }, 220);
      });

      // 双击：直接搜这本书（不走选中逻辑、不动输入框）
      chip.addEventListener('dblclick', function (e) {
        e.stopPropagation();
        if (clickTimer) {
          clearTimeout(clickTimer);
          clickTimer = null;
        }
        window.searchOneBook(b.name);
      });

      // 右键：菜单
      chip.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        window.showBookmarkMenu(e.clientX, e.clientY, b.id, b.name);
      });

      bookmarkRow.appendChild(chip);
    });
  };

  /* 书签右键菜单 */
  window.showBookmarkMenu = function (x, y, bmId, bmName) {
    var menu = document.getElementById('bmContextMenu');
    if (!menu) {
      menu = document.createElement('div');
      menu.id = 'bmContextMenu';
      menu.style.cssText = 'position:fixed;background:#fff;border:1px solid #E8EBEE;' +
        'border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,0.1);padding:4px 0;' +
        'z-index:9999;display:none;min-width:140px;';
      menu.innerHTML =
        '<div class="bm-menu-item" data-action="fill">填入输入框</div>' +
        '<div class="bm-menu-item" data-action="delete" style="color:#E63946;">删除书签</div>';
      document.body.appendChild(menu);
    }
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    menu.style.display = 'block';
    menu.dataset.bmId = bmId;
    menu.dataset.bmName = bmName;

    menu.onclick = function (ev) {
      var item = ev.target.closest('.bm-menu-item');
      if (!item) { return; }
      var action = item.dataset.action;
      if (action === 'fill') {
        bookInput.value = bmName;
      } else if (action === 'delete') {
        if (window.confirm('确定删除书签「' + bmName + '」？')) {
          if (apiReady()) { window.pywebview.api.delete_bookmark(bmId); }
        }
      }
      menu.style.display = 'none';
    };
  };

  /* 点别处关闭菜单 */
  document.addEventListener('click', function (e) {
    var menu = document.getElementById('bmContextMenu');
    if (menu && !menu.contains(e.target)) { menu.style.display = 'none'; }
  });

  /* ==================== 后缀浮层（批 3-B） ==================== */
  window.openSuffixPopup = function (bmId, chipEl) {
    var popup = document.getElementById('suffixPopup');
    if (!popup) { return; }
    if (!requireApi()) { return; }
    window.pywebview.api.get_bookmarks().then(function (books) {
      var bm = (books || []).find(function (b) { return b.id === bmId; });
      if (!bm) { return; }
      renderSuffixPopup(bm);
      // 定位：胶囊下方
      var rect = chipEl.getBoundingClientRect();
      popup.style.left = rect.left + 'px';
      popup.style.top = (rect.bottom + 4) + 'px';
      popup.style.display = 'block';
    });
  };

  function renderSuffixPopup(bm) {
    var popup = document.getElementById('suffixPopup');
    var html = '<div class="sf-popup-title">「' + bm.name +
               '」的搜索词（勾选=参与搜索）</div>';

    bm.suffixes.forEach(function (s, idx) {
      var display = s.text || '无后缀';
      var checked = s.enabled ? 'checked' : '';
      var delBtn = s.text
        ? '<span class="sf-del" data-idx="' + idx + '">✕</span>' : '';
      html += '<div class="sf-item">' +
                '<input type="checkbox" class="sf-cb" data-idx="' + idx + '" ' +
                  checked + '>' +
                '<label>' + display + '</label>' +
                delBtn +
              '</div>';
    });

    html += '<div class="sf-add-row">' +
              '<input type="text" id="sfNewInput" placeholder="新后缀，回车添加">' +
              '<button id="sfAddBtn">+</button>' +
            '</div>';

    popup.innerHTML = html;
    popup.dataset.bmId = bm.id;

    // 勾选切换
    popup.querySelectorAll('.sf-cb').forEach(function (cb) {
      cb.addEventListener('change', function () {
        var idx = parseInt(getDataset(cb).idx, 10);
        if (isNaN(idx) || idx < 0 || idx >= bm.suffixes.length) { return; }
        bm.suffixes[idx].enabled = cb.checked;
        saveSuffixes(bm, false);
      });
    });

    // 删除
    popup.querySelectorAll('.sf-del').forEach(function (el) {
      el.addEventListener('click', function () {
        var idx = parseInt(getDataset(el).idx, 10);
        if (isNaN(idx) || idx < 0 || idx >= bm.suffixes.length) { return; }
        bm.suffixes.splice(idx, 1);
        saveSuffixes(bm, true);       // true = 重新渲染浮层
      });
    });

    // 新增
    function doAdd() {
      var inp = document.getElementById('sfNewInput');
      var txt = (inp.value || '').trim();
      if (!txt) { return; }
      var exists = bm.suffixes.some(function (s) { return s.text === txt; });
      if (exists) { inp.value = ''; return; }     // 去重
      bm.suffixes.push({ text: txt, enabled: true });
      saveSuffixes(bm, true);
    }

    document.getElementById('sfAddBtn').addEventListener('click', doAdd);
    document.getElementById('sfNewInput').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); doAdd(); }
    });
  }

  function saveSuffixes(bm, rerender) {
    window.pywebview.api.update_bookmark_suffixes(bm.id, bm.suffixes)
      .then(function () {
        if (rerender) { renderSuffixPopup(bm); }
      });
  }

  /* 点别处关闭浮层（点在 ▼ 箭头上时交给 openSuffixPopup 处理） */
  document.addEventListener('click', function (e) {
    var popup = document.getElementById('suffixPopup');
    if (!popup || popup.style.display !== 'block') { return; }
    if (popup.contains(e.target)) { return; }
    if (e.target.classList && e.target.classList.contains('bm-arrow')) { return; }
    popup.style.display = 'none';
  });

  /* Esc 关闭浮层 */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      var popup = document.getElementById('suffixPopup');
      if (popup) { popup.style.display = 'none'; }
    }
  });

  /* 「保存为书签」：取输入框书名 → 后端新建（允许重名） */
  if (btnBookmark) {
    btnBookmark.addEventListener('click', function () {
      var name = (bookInput.value || '').trim();
      if (!name) { window.appendLog('[提示] 请先输入书名'); return; }
      if (!requireApi()) { return; }
      window.pywebview.api.add_bookmark(name);
    });
  }

  /* 启动时拉一次书签列表 */
  if (apiReady()) { loadBookmarks(); }
  window.addEventListener('pywebviewready', loadBookmarks);

  /* 初始状态：搜索按钮可用、停止按钮禁用 */
  window.setSearching(false);
})();

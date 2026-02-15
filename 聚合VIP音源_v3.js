/**
 * @name 聚合VIP完整版 (星海+汽水)
 * @description 集成五大平台(基于GD接口)与汽水音乐VIP源，全音质支持。
 * @version 3.0.0
 * @author 整合: Gemini / 原作: 万去了了, 歌一刀
 */

const { EVENT_NAMES, request, on, send, utils } = globalThis.lx;

// ================= 配置区域 =================
const CONFIG = {
  // GD Studio 主接口 (用于五大平台)
  mainApi: 'https://music-api.gdstudio.xyz/api.php',
  // 汽水音乐接口
  qsApi: 'http://api.vsaa.cn/api/music.qishui.vip',
  qsProxy: 'https://proxy.qishui.vsaa.cn/qishui/proxy'
};

// ================= 工具函数 =================
const http = (url, options = {}) => {
  return new Promise((resolve, reject) => {
    request(url, {
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        ...options.headers
      },
      ...options
    }, (err, resp) => {
      if (err) return reject(err);
      resolve(resp);
    });
  });
};

// 辅助：构建Query字符串
function buildQuery(params) {
  const parts = [];
  for (const k in params) {
    if (params[k] !== undefined && params[k] !== null) {
      parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(params[k]));
    }
  }
  return parts.length ? ('?' + parts.join('&')) : '';
}

// ================= 模块一：五大主流平台 (GDStudio) =================
// 包含: 网易云(wy), QQ(tx), 酷我(kw), 酷狗(kg), 咪咕(mg)

const MainProvider = {
  // 质量映射
  qualityMap: {
    '128k': '128',
    '320k': '320',
    'flac': '740',      // 16bit
    'flac24bit': '999', // 24bit Hi-Res
    'master': '999'
  },

  // 接口源映射
  sourceMap: {
    'wy': 'netease',
    'tx': 'tencent',
    'kw': 'kuwo',
    'kg': 'kugou',
    'mg': 'migu'
  },

  async getUrl(source, musicInfo, quality) {
    const apiSource = this.sourceMap[source];
    if (!apiSource) throw new Error('不支持的源类型');

    const songId = musicInfo.hash || musicInfo.songmid || musicInfo.id;
    // 默认降级策略：如果请求的高音质失败，API通常会返回由低一级的链接，无需前端做过多处理
    // 但为了保险，我们映射一下质量参数
    const br = this.qualityMap[quality] || '320';

    const targetUrl = `${CONFIG.mainApi}?types=url&source=${apiSource}&id=${songId}&br=${br}`;
    
    try {
      const resp = await http(targetUrl);
      const body = typeof resp.body === 'string' ? JSON.parse(resp.body) : resp.body;
      
      if (!body || !body.url) throw new Error('接口返回数据为空');
      return body.url;
    } catch (e) {
      console.error(`[MainProvider] 获取连接失败: ${e.message}`);
      throw e;
    }
  }
};

// ================= 模块二：汽水音乐 (QSVIP) =================
// 包含: 汽水VIP(qsvip) - 独立搜索和播放逻辑

const QsProvider = {
  // 格式化歌曲信息适配 LX
  normalize(item) {
    const id = (item && (item.id || item.vid)) ? String(item.id || item.vid) : '';
    return {
      id,
      songmid: id,
      name: (item && item.name) ? String(item.name) : '未知歌曲',
      singer: (item && item.artists) ? String(item.artists) : '未知歌手',
      albumName: (item && item.album) ? String(item.album) : '',
      duration: item && item.duration ? Math.floor(Number(item.duration) / 1000) : 0,
      pic: item && (item.cover || item.pic) ? String(item.cover || item.pic) : '',
      _raw: item || {},
    };
  },

  async search(keyword, page, limit) {
    const resp = await http(CONFIG.qsApi + buildQuery({
      act: 'search',
      keywords: keyword,
      page,
      pagesize: limit,
      type: 'music'
    }), { timeout: 15000 });

    const body = typeof resp.body === 'string' ? JSON.parse(resp.body) : resp.body;
    const lists = (body && body.data && Array.isArray(body.data.lists)) ? body.data.lists : [];
    const total = (body && body.data && body.data.total) ? Number(body.data.total) : lists.length;
    
    return {
      isEnd: lists.length < limit,
      list: lists.map(this.normalize),
      total
    };
  },

  async getUrl(musicInfo, quality) {
    const id = musicInfo.songmid || musicInfo.id;
    // 映射音质
    let q = 'standard';
    if (quality === '128k') q = 'low';
    if (quality === 'flac') q = 'lossless';
    if (quality === 'flac24bit') q = 'hi_res';

    const resp = await http(CONFIG.qsApi + buildQuery({ act: 'song', id, quality: q }), { timeout: 20000 });
    const body = typeof resp.body === 'string' ? JSON.parse(resp.body) : resp.body;
    
    const song = (body && Array.isArray(body.data)) ? body.data[0] : (body && body.data && body.data[0]) ? body.data[0] : null;
    if (!song || !song.url) throw new Error('未找到汽水音乐链接');

    // 处理加密链接 (ekey)
    if (song.ekey) {
      const proxyResp = await http(CONFIG.qsProxy, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: song.url,
          key: song.ekey,
          filename: song.name || 'KMusic',
          ext: song.codec_type || 'aac',
        }),
        timeout: 60000
      });
      const proxyBody = typeof proxyResp.body === 'string' ? JSON.parse(proxyResp.body) : proxyResp.body;
      if (proxyBody && proxyBody.code == 200 && proxyBody.url) {
        return proxyBody.url;
      }
    }
    return song.url;
  },

  async getLyric(musicInfo) {
    const id = musicInfo.songmid || musicInfo.id;
    const resp = await http(CONFIG.qsApi + buildQuery({ act: 'song', id }), { timeout: 15000 });
    const body = typeof resp.body === 'string' ? JSON.parse(resp.body) : resp.body;
    
    const song = (body && Array.isArray(body.data)) ? body.data[0] : (body && body.data && body.data[0]) ? body.data[0] : null;
    return { lyric: song && song.lyric ? String(song.lyric) : '' };
  }
};

// ================= 核心处理逻辑 =================

on(EVENT_NAMES.request, async ({ action, source, info }) => {
  try {
    // ---------------- 汽水音乐处理逻辑 ----------------
    if (source === 'qsvip') {
      if (action === 'musicSearch' || action === 'search') {
        return await QsProvider.search(info.keyword, info.page, info.limit);
      }
      if (action === 'musicUrl') {
        return await QsProvider.getUrl(info.musicInfo, info.type);
      }
      if (action === 'lyric') {
        return await QsProvider.getLyric(info.musicInfo);
      }
    } 
    // ---------------- 五大主流平台处理逻辑 ----------------
    else {
      if (action === 'musicUrl') {
        return await MainProvider.getUrl(source, info.musicInfo, info.type);
      }
    }
  } catch (err) {
    console.error(`[聚合API] ${source} - ${action} 失败:`, err);
    return Promise.reject(err);
  }
});

// ================= 初始化注册 =================
const commonQualities = ['128k', '320k', 'flac', 'flac24bit'];

send(EVENT_NAMES.inited, {
  status: true,
  openDevTools: false,
  sources: {
    // 五大主流平台 (仅需注册musicUrl，搜索走洛雪内置)
    'kw': {
      name: '酷我音乐',
      type: 'music',
      actions: ['musicUrl'],
      qualitys: commonQualities
    },
    'kg': {
      name: '酷狗音乐',
      type: 'music',
      actions: ['musicUrl'],
      qualitys: commonQualities
    },
    'tx': {
      name: 'QQ音乐',
      type: 'music',
      actions: ['musicUrl'],
      qualitys: commonQualities
    },
    'wy': {
      name: '网易云音乐',
      type: 'music',
      actions: ['musicUrl'],
      qualitys: ['128k', '320k', 'flac'] // 网易通常无24bit接口
    },
    'mg': {
      name: '咪咕音乐',
      type: 'music',
      actions: ['musicUrl'],
      qualitys: commonQualities
    },
    // 汽水音乐 (自定义源，需注册搜索)
    'qsvip': {
      name: '汽水VIP',
      type: 'music',
      actions: ['musicSearch', 'musicUrl', 'lyric'],
      qualitys: commonQualities
    }
  }
});

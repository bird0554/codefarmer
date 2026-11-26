import { CSSProperties, FormEvent, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlarmClock,
  ArrowDownWideNarrow,
  ArrowRight,
  Bell,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Clock3,
  FileText,
  Filter,
  Inbox,
  LayoutDashboard,
  LifeBuoy,
  ListFilter,
  MessageSquare,
  MoreHorizontal,
  Paperclip,
  Plus,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  Users,
  X,
} from 'lucide-react';
import './ticket-flow.css';

type TicketStatus = '待受理' | '处理中' | '等待客户' | '已解决';
type TicketPriority = '紧急' | '高' | '普通' | '低';

type Ticket = {
  id: string;
  title: string;
  category: string;
  status: TicketStatus;
  priority: TicketPriority;
  requester: string;
  requesterTeam: string;
  assignee: string;
  assigneeInitials: string;
  updated: string;
  created: string;
  description: string;
  messages: number;
};

type TicketFilter = '全部' | '待受理' | '处理中' | '等待客户' | '已解决' | '我负责的' | '我发起的';
type TicketTheme = 'forest' | 'ocean' | 'amber';
type TicketFontSize = 'standard' | 'large' | 'xlarge';

const themeOptions: Array<{ id: TicketTheme; label: string; accent: string; accentDark: string; accentSoft: string; sidebar: string; sidebarHover: string; sidebarActive: string; sidebarMark: string; selected: string }> = [
  { id: 'forest', label: '森林绿', accent: '#28785f', accentDark: '#205e4b', accentSoft: '#eaf4ef', sidebar: '#1e2d26', sidebarHover: '#2a3b32', sidebarActive: '#31473b', sidebarMark: '#36785e', selected: '#f3f8f4' },
  { id: 'ocean', label: '海岸蓝', accent: '#2d6fa3', accentDark: '#24577f', accentSoft: '#eaf3fb', sidebar: '#1d2a38', sidebarHover: '#273b4f', sidebarActive: '#2d465b', sidebarMark: '#3d86b3', selected: '#eff6fb' },
  { id: 'amber', label: '暖棕色', accent: '#a06b2c', accentDark: '#815421', accentSoft: '#fbf3e6', sidebar: '#352b21', sidebarHover: '#473a2b', sidebarActive: '#584633', sidebarMark: '#b57b36', selected: '#fdf6e9' },
];

const fontSizeOptions: Array<{ id: TicketFontSize; label: string; scale: number }> = [
  { id: 'standard', label: '标准', scale: 1.1 },
  { id: 'large', label: '大', scale: 1.22 },
  { id: 'xlarge', label: '特大', scale: 1.36 },
];

function readAppearanceSetting<T extends string>(key: string, fallback: T, allowed: readonly T[]): T {
  try {
    const value = window.localStorage.getItem(key) as T | null;
    return value && allowed.includes(value) ? value : fallback;
  } catch {
    return fallback;
  }
}

const initialTickets: Ticket[] = [
  {
    id: 'TK-2026-0842',
    title: '数据看板导出后字段顺序错乱',
    category: '产品与功能',
    status: '处理中',
    priority: '高',
    requester: '林晓宁',
    requesterTeam: '增长运营',
    assignee: '周启明',
    assigneeInitials: '周',
    updated: '3 分钟前',
    created: '今天 09:14',
    description: '月度渠道报表导出为 Excel 后，字段顺序与页面上配置的不一致。今天的复盘会需要用到这份数据，希望能帮忙确认一下。',
    messages: 4,
  },
  {
    id: 'TK-2026-0841',
    title: '新同事无法加入「华东交付」工作区',
    category: '账户与权限',
    status: '待受理',
    priority: '紧急',
    requester: '陈安然',
    requesterTeam: '交付中心',
    assignee: '未分配',
    assigneeInitials: '—',
    updated: '8 分钟前',
    created: '今天 09:09',
    description: '邀请链接显示已过期，但管理员刚刚生成了新的链接。该同事今天需要参与客户项目交接。',
    messages: 2,
  },
  {
    id: 'TK-2026-0839',
    title: '审批流程在第二位负责人处停滞',
    category: '流程审批',
    status: '等待客户',
    priority: '普通',
    requester: '王一帆',
    requesterTeam: '财务部',
    assignee: '许若溪',
    assigneeInitials: '许',
    updated: '24 分钟前',
    created: '今天 08:42',
    description: '采购申请提交后，审批记录停留在第二位负责人处。负责人表示已经在手机端完成审批，但流程没有继续。',
    messages: 3,
  },
  {
    id: 'TK-2026-0837',
    title: '移动端消息提醒时间与设置不一致',
    category: '产品与功能',
    status: '处理中',
    priority: '普通',
    requester: '赵可心',
    requesterTeam: '设计团队',
    assignee: '周启明',
    assigneeInitials: '周',
    updated: '41 分钟前',
    created: '今天 08:21',
    description: '已将免打扰时间设置为 22:00 至 08:00，早上七点仍收到了项目动态推送。',
    messages: 5,
  },
  {
    id: 'TK-2026-0835',
    title: '申请开通测试环境只读权限',
    category: '账户与权限',
    status: '已解决',
    priority: '低',
    requester: '何景明',
    requesterTeam: '数据平台',
    assignee: '许若溪',
    assigneeInitials: '许',
    updated: '1 小时前',
    created: '今天 07:56',
    description: '为本周的数据迁移演练申请测试环境的只读查询权限。',
    messages: 2,
  },
  {
    id: 'TK-2026-0833',
    title: '客户名称批量更新后没有同步到合同页',
    category: '数据问题',
    status: '处理中',
    priority: '高',
    requester: '蒋思远',
    requesterTeam: '销售运营',
    assignee: '林予安',
    assigneeInitials: '林',
    updated: '1 小时前',
    created: '今天 07:38',
    description: '批量更新了客户主体名称，客户资料页已经正确显示，关联合同页面仍保留旧名称。',
    messages: 6,
  },
];

const filterOptions: TicketFilter[] = ['全部', '待受理', '处理中', '等待客户', '已解决', '我负责的', '我发起的'];

function statusClass(status: TicketStatus) {
  return status.replace(' ', '');
}

function initials(name: string) {
  return name.slice(0, 1);
}

function TicketFlowPage() {
  const [tickets, setTickets] = useState(initialTickets);
  const [selectedId, setSelectedId] = useState(initialTickets[0].id);
  const [activeFilter, setActiveFilter] = useState<TicketFilter>('全部');
  const [query, setQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('全部优先级');
  const [newestFirst, setNewestFirst] = useState(true);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [toast, setToast] = useState('');
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('产品与功能');
  const [priority, setPriority] = useState<TicketPriority>('普通');
  const [description, setDescription] = useState('');
  const [theme, setTheme] = useState<TicketTheme>(() => readAppearanceSetting('ticket-theme', 'forest', themeOptions.map(option => option.id)));
  const [fontSize, setFontSize] = useState<TicketFontSize>(() => readAppearanceSetting('ticket-font-size', 'standard', fontSizeOptions.map(option => option.id)));
  const [isAppearanceOpen, setIsAppearanceOpen] = useState(false);

  const activeTheme = themeOptions.find(option => option.id === theme) ?? themeOptions[0];
  const activeFontSize = fontSizeOptions.find(option => option.id === fontSize) ?? fontSizeOptions[0];
  const appearanceStyle = {
    '--ink': '#202923',
    '--canvas': '#f7f9f6',
    '--green': activeTheme.accent,
    '--green-dark': activeTheme.accentDark,
    '--green-soft': activeTheme.accentSoft,
    '--accent': activeTheme.accent,
    '--accent-dark': activeTheme.accentDark,
    '--accent-soft': activeTheme.accentSoft,
    '--sidebar': activeTheme.sidebar,
    '--sidebar-hover': activeTheme.sidebarHover,
    '--sidebar-active': activeTheme.sidebarActive,
    '--sidebar-mark': activeTheme.sidebarMark,
    '--selected': activeTheme.selected,
    '--focus': activeTheme.accent,
    '--font-scale': activeFontSize.scale,
  } as CSSProperties;

  const selectedTicket = tickets.find(ticket => ticket.id === selectedId);
  const counts = useMemo(() => ({
    全部: tickets.length,
    待受理: tickets.filter(ticket => ticket.status === '待受理').length,
    处理中: tickets.filter(ticket => ticket.status === '处理中').length,
    等待客户: tickets.filter(ticket => ticket.status === '等待客户').length,
    已解决: tickets.filter(ticket => ticket.status === '已解决').length,
    我负责的: tickets.filter(ticket => ticket.assignee === '林予安').length,
    我发起的: tickets.filter(ticket => ticket.requester === '林予安').length,
  }), [tickets]);
  const pendingCount = tickets.filter(ticket => ticket.status !== '已解决').length;

  const visibleTickets = useMemo(() => {
    const filtered = tickets.filter(ticket => {
    const matchesFilter = activeFilter === '全部'
      || ticket.status === activeFilter
      || (activeFilter === '我负责的' && ticket.assignee === '林予安')
      || (activeFilter === '我发起的' && ticket.requester === '林予安');
    const searchText = `${ticket.id} ${ticket.title} ${ticket.requester} ${ticket.assignee}`.toLowerCase();
    const matchesQuery = !query.trim() || searchText.includes(query.trim().toLowerCase());
    const matchesPriority = priorityFilter === '全部优先级' || ticket.priority === priorityFilter;
    return matchesFilter && matchesQuery && matchesPriority;
    });
    return newestFirst ? filtered : filtered.reverse();
  }, [tickets, activeFilter, query, priorityFilter, newestFirst]);

  useEffect(() => {
    if (!isCreateOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsCreateOpen(false);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [isCreateOpen]);

  useEffect(() => {
    try {
      window.localStorage.setItem('ticket-theme', theme);
      window.localStorage.setItem('ticket-font-size', fontSize);
    } catch {
      // Appearance settings still apply for this session when storage is unavailable.
    }
  }, [theme, fontSize]);

  useEffect(() => {
    if (!isAppearanceOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsAppearanceOpen(false);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [isAppearanceOpen]);

  const resetAppearance = () => {
    setTheme('forest');
    setFontSize('standard');
    notify('界面设置已恢复默认');
  };

  const notify = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(''), 2800);
  };

  const moveTicketForward = () => {
    if (!selectedTicket) return;
    const nextStatus: Record<TicketStatus, TicketStatus> = {
      待受理: '处理中',
      处理中: '已解决',
      等待客户: '处理中',
      已解决: '已解决',
    };
    const next = nextStatus[selectedTicket.status];
    if (next === selectedTicket.status) {
      notify('该工单已完成');
      return;
    }
    const autoAssign = selectedTicket.assignee === '未分配' && next === '处理中';
    setTickets(current => current.map(ticket => ticket.id === selectedId
      ? { ...ticket, status: next, updated: '刚刚', ...(autoAssign ? { assignee: '林予安', assigneeInitials: '林' } : {}) }
      : ticket));
    notify(`工单已流转至「${next}」`);
  };

  const waitForCustomer = () => {
    if (!selectedTicket) return;
    setTickets(current => current.map(ticket => ticket.id === selectedId
      ? { ...ticket, status: '等待客户', updated: '刚刚' }
      : ticket));
    notify('工单已转入等待客户');
  };

  const assignToMe = () => {
    if (!selectedTicket) return;
    setTickets(current => current.map(ticket => ticket.id === selectedId
      ? { ...ticket, assignee: '林予安', assigneeInitials: '林', updated: '刚刚' }
      : ticket));
    notify('已指派给林予安');
  };

  const createTicket = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextTicket: Ticket = {
      id: `TK-2026-${String(843 + tickets.length - initialTickets.length).padStart(4, '0')}`,
      title: title.trim(),
      category,
      status: '待受理',
      priority,
      requester: '林予安',
      requesterTeam: '增长运营',
      assignee: '未分配',
      assigneeInitials: '—',
      updated: '刚刚',
      created: '今天 09:42',
      description: description.trim(),
      messages: 0,
    };
    setTickets(current => [nextTicket, ...current]);
    setSelectedId(nextTicket.id);
    setActiveFilter('全部');
    setQuery('');
    setIsCreateOpen(false);
    setTitle('');
    setDescription('');
    notify('工单已创建并进入待受理队列');
  };

  return (
    <div className="ticket-app" data-font-size={fontSize} style={appearanceStyle}>
      <aside className="ticket-sidebar">
        <a className="ticket-brand" href="/tickets" aria-label="启序工单首页">
          <span className="ticket-brand-mark"><Activity size={18} strokeWidth={2.5} /></span>
          <span><strong>启序</strong><small>WORKFLOW DESK</small></span>
        </a>

        <div className="sidebar-workspace">
          <span className="workspace-avatar">Q</span>
          <span><strong>启序科技</strong><small>企业工作区</small></span>
          <ChevronDown size={15} />
        </div>

        <p className="sidebar-label">工作空间</p>
        <nav className="ticket-nav" aria-label="主导航">
          <button className="ticket-nav-item" type="button" onClick={() => notify('工作台正在加载')}><LayoutDashboard size={17} />工作台</button>
          <button className={`ticket-nav-item ${activeFilter === '全部' ? 'active' : ''}`} type="button" onClick={() => setActiveFilter('全部')}><Inbox size={17} />工单收件箱<span className="nav-count">{counts.全部}</span></button>
          <button className={`ticket-nav-item ${activeFilter === '我负责的' ? 'active' : ''}`} type="button" onClick={() => setActiveFilter('我负责的')}><CircleDot size={17} />我负责的<span className="nav-count soft">{counts.我负责的}</span></button>
          <button className="ticket-nav-item" type="button" onClick={() => setActiveFilter('我发起的')}><Send size={17} />我发起的</button>
        </nav>

        <p className="sidebar-label second-label">管理</p>
        <nav className="ticket-nav" aria-label="管理导航">
          <button className="ticket-nav-item" type="button" onClick={() => notify('服务目录已是最新')}><FileText size={17} />服务目录</button>
          <button className="ticket-nav-item" type="button" onClick={() => notify('知识库正在整理中')}><ShieldCheck size={17} />知识库</button>
          <button className="ticket-nav-item" type="button" onClick={() => notify('团队成员 12 人')}><Users size={17} />团队与排班</button>
        </nav>

        <div className="sidebar-bottom">
          <div className="online-status"><span />所有系统运行正常</div>
          <button className={`ticket-nav-item ${isAppearanceOpen ? 'active' : ''}`} type="button" aria-expanded={isAppearanceOpen} onClick={() => setIsAppearanceOpen(current => !current)}><Settings2 size={17} />界面设置</button>
          <button className="sidebar-profile" type="button" onClick={() => notify('当前账户：林予安')}>
            <span className="person-avatar avatar-lin">林</span>
            <span><strong>林予安</strong><small>支持专员</small></span>
            <MoreHorizontal size={18} />
          </button>
        </div>
      </aside>

      <main className="ticket-main">
        <header className="ticket-topbar">
          <div className="breadcrumb"><span>工作空间</span><ChevronRight size={14} /><strong>工单流转</strong></div>
          <div className="topbar-actions">
            <label className="global-search"><Search size={16} /><input aria-label="搜索工单" placeholder="搜索工单、成员..." value={query} onChange={event => setQuery(event.target.value)} /><kbd>⌘ K</kbd></label>
            <button className="icon-button notification-button" type="button" aria-label="通知" title="通知" onClick={() => notify('目前没有新的通知')}><Bell size={17} /><i /></button>
            <button className={`icon-button appearance-button ${isAppearanceOpen ? 'active' : ''}`} type="button" aria-label="界面设置" aria-expanded={isAppearanceOpen} title="界面设置" onClick={() => setIsAppearanceOpen(current => !current)}><Settings2 size={17} /></button>
            <span className="topbar-divider" />
            <button className="person-avatar avatar-lin topbar-avatar" type="button" aria-label="林予安账户" onClick={() => notify('当前账户：林予安')}>林</button>
          </div>
        </header>

        {isAppearanceOpen && <section className="appearance-panel" aria-label="界面设置">
          <div className="appearance-panel-heading"><div><span className="appearance-panel-icon"><Settings2 size={16} /></span><div><strong>界面设置</strong><small>字号与主题会自动保存</small></div></div><button className="icon-button" type="button" aria-label="关闭界面设置" title="关闭" onClick={() => setIsAppearanceOpen(false)}><X size={16} /></button></div>
          <div className="appearance-group"><div className="appearance-group-label"><strong>界面字号</strong><span>放大列表、详情与表单文字</span></div><div className="appearance-options" role="group" aria-label="界面字号">
            {fontSizeOptions.map(option => <button key={option.id} type="button" className={`appearance-option ${fontSize === option.id ? 'selected' : ''}`} aria-pressed={fontSize === option.id} onClick={() => setFontSize(option.id)}><span className={`font-preview font-preview-${option.id}`}>Aa</span><span>{option.label}</span>{fontSize === option.id && <Check size={14} />}</button>)}
          </div></div>
          <div className="appearance-group"><div className="appearance-group-label"><strong>主题配色</strong><span>调整强调色、侧栏与选中状态</span></div><div className="theme-options" role="group" aria-label="主题配色">
            {themeOptions.map(option => <button key={option.id} type="button" className={`theme-option ${theme === option.id ? 'selected' : ''}`} aria-pressed={theme === option.id} onClick={() => setTheme(option.id)}><span className="theme-swatch" style={{ background: option.accent }} /><span>{option.label}</span>{theme === option.id && <Check size={14} />}</button>)}
          </div></div>
          <div className="appearance-panel-footer"><button type="button" className="reset-appearance" onClick={resetAppearance}>恢复默认</button><span><CheckCircle2 size={13} />已自动保存</span></div>
        </section>}

        <div className="ticket-content">
          <div className="page-title-row">
            <div>
              <div className="eyebrow"><span className="eyebrow-dot" />服务运营 <span>/</span> 工单队列</div>
              <h1>工单流转</h1>
              <p>集中处理请求，保持每一次协作都有序推进。</p>
            </div>
            <div className="title-actions">
              <div className="on-duty"><span className="duty-avatars"><i>周</i><i>许</i><i>林</i></span><span>3 人在线</span></div>
              <button className="create-ticket-button" type="button" onClick={() => setIsCreateOpen(true)}><Plus size={17} />新建工单</button>
            </div>
          </div>

          <section className="metric-strip" aria-label="工单概况">
            <div className="metric-item"><div className="metric-icon metric-inbox"><Inbox size={17} /></div><div><span>待处理工单</span><strong>{pendingCount} <small>件</small></strong></div><em className="metric-change">实时</em></div>
            <div className="metric-item"><div className="metric-icon metric-clock"><AlarmClock size={17} /></div><div><span>即将超时</span><strong>03 <small>件</small></strong></div><em className="metric-warning">需要关注</em></div>
            <div className="metric-item"><div className="metric-icon metric-resolve"><CheckCircle2 size={17} /></div><div><span>平均解决时长</span><strong>2.4 <small>小时</small></strong></div><em className="metric-change">↓ 12% 本周</em></div>
            <div className="metric-item satisfaction-item"><div className="metric-icon metric-satisfaction"><MessageSquare size={17} /></div><div><span>本周满意度</span><strong>98.6<small>%</small></strong></div><div className="satisfaction-bars" aria-label="满意度趋势稳定"><i /><i /><i /><i /><i /><i /><i /></div></div>
          </section>

          <section className="queue-section" aria-label="工单队列">
            <div className="queue-heading">
              <div><h2>服务队列</h2><span>实时更新 · 最后同步 09:42</span></div>
              <button className="text-tool" type="button" onClick={() => notify('队列已刷新')}><Activity size={15} />实时队列</button>
            </div>

            <div className="queue-tabs" role="tablist" aria-label="工单状态筛选">
              {filterOptions.map(filter => (
                <button key={filter} type="button" role="tab" aria-selected={activeFilter === filter} className={activeFilter === filter ? 'selected' : ''} onClick={() => setActiveFilter(filter)}>
                  {filter}<span>{counts[filter as keyof typeof counts]}</span>
                </button>
              ))}
            </div>

            <div className="queue-toolbar">
              <div className="queue-search"><Search size={15} /><input aria-label="搜索当前队列" placeholder="按主题或编号搜索" value={query} onChange={event => setQuery(event.target.value)} /></div>
              <div className="queue-tools">
                <label className="priority-select"><Filter size={14} /><select aria-label="按优先级筛选" value={priorityFilter} onChange={event => setPriorityFilter(event.target.value)}><option>全部优先级</option><option>紧急</option><option>高</option><option>普通</option><option>低</option></select><ChevronDown size={13} /></label>
                <button className="icon-button filter-button" type="button" aria-label="更多筛选" onClick={() => notify('当前已显示所有团队工单')}><ListFilter size={16} /></button>
                <button className="icon-button sort-button" type="button" aria-label={newestFirst ? '切换为较早工单优先' : '切换为最新工单优先'} onClick={() => setNewestFirst(current => !current)}><ArrowDownWideNarrow size={16} /></button>
              </div>
            </div>

            <div className="ticket-table-wrap">
              <table className="ticket-table">
                <thead><tr><th className="check-column"><input aria-label="选择全部工单" type="checkbox" onChange={event => event.currentTarget.checked && notify('已选择当前页工单')} /></th><th>工单主题</th><th>状态</th><th>优先级</th><th>申请人</th><th>处理人</th><th>更新时间</th></tr></thead>
                <tbody>
                  {visibleTickets.map(ticket => (
                    <tr key={ticket.id} className={selectedId === ticket.id ? 'ticket-row selected-row' : 'ticket-row'} onClick={() => setSelectedId(ticket.id)} tabIndex={0} aria-selected={selectedId === ticket.id} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelectedId(ticket.id); } }}>
                      <td className="check-column" onClick={event => event.stopPropagation()}><input aria-label={`选择工单 ${ticket.id}`} type="checkbox" /></td>
                      <td className="subject-cell"><strong>{ticket.title}</strong><span><code>{ticket.id}</code><i />{ticket.category}</span></td>
                      <td><span className={`status-pill status-${statusClass(ticket.status)}`}><i />{ticket.status}</span></td>
                      <td><span className={`priority-label priority-${ticket.priority}`}>{ticket.priority === '紧急' && <span className="priority-mark">↑</span>}{ticket.priority}</span></td>
                      <td><span className="requester-cell"><i className="requester-avatar">{initials(ticket.requester)}</i>{ticket.requester}</span></td>
                      <td><span className="assignee-cell"><i className={`person-avatar table-avatar ${ticket.assigneeInitials === '—' ? 'unassigned-avatar' : ''}`}>{ticket.assigneeInitials}</i>{ticket.assignee}</span></td>
                      <td className="updated-cell">{ticket.updated}</td>
                    </tr>
                  ))}
                  {!visibleTickets.length && <tr><td className="empty-row" colSpan={7}><Inbox size={22} /><strong>没有符合条件的工单</strong><span>试试调整筛选条件或搜索内容。</span></td></tr>}
                </tbody>
              </table>
            </div>
            <footer className="table-footer"><span>显示 <strong>{visibleTickets.length ? 1 : 0}–{visibleTickets.length}</strong> 条，共 <strong>{visibleTickets.length}</strong> 条工单</span><div><button type="button" aria-label="上一页" disabled><ChevronRight className="previous-page" size={15} /></button><button type="button" className="current-page">1</button><button type="button" aria-label="下一页" disabled><ChevronRight size={15} /></button></div></footer>
          </section>

          <aside className="ticket-detail" aria-label="工单详情">
            {selectedTicket ? <>
              <div className="detail-topline"><span className="detail-id">{selectedTicket.id}</span><div><button className="icon-button" type="button" aria-label="更多工单操作" onClick={() => notify('更多操作已展开')}><MoreHorizontal size={18} /></button><button className="icon-button" type="button" aria-label="关闭工单详情" onClick={() => setSelectedId('')}><X size={17} /></button></div></div>
              <div className="detail-title-block"><span className={`status-pill status-${statusClass(selectedTicket.status)}`}><i />{selectedTicket.status}</span><h2>{selectedTicket.title}</h2><div className="detail-meta"><span><CalendarDays size={14} />创建于 {selectedTicket.created}</span><span><MessageSquare size={14} />{selectedTicket.messages} 条回复</span></div></div>
              <div className="detail-priority-row"><span>优先级</span><strong className={`priority-label priority-${selectedTicket.priority}`}>{selectedTicket.priority}</strong><span className="detail-category">{selectedTicket.category}</span></div>

              <div className="flow-card">
                <div className="flow-card-heading"><span><Activity size={15} />流转进度</span><button type="button" aria-label="流转设置" onClick={() => notify('流转规则由工作区管理员维护')}><Settings2 size={15} /></button></div>
                <div className="flow-steps">
                  <div className="flow-step done"><span><Check size={12} /></span><div><strong>提交申请</strong><small>{selectedTicket.requester} · {selectedTicket.created}</small></div></div>
                  <div className={`flow-connector ${selectedTicket.status !== '待受理' ? 'complete' : ''}`} />
                  <div className={`flow-step ${selectedTicket.status !== '待受理' ? 'done' : 'current'}`}><span>{selectedTicket.status !== '待受理' ? <Check size={12} /> : '2'}</span><div><strong>支持团队处理</strong><small>{selectedTicket.status === '待受理' ? '等待分派处理' : `${selectedTicket.assignee} · 正在处理`}</small></div></div>
                  <div className={`flow-connector ${selectedTicket.status === '已解决' ? 'complete' : ''}`} />
                  <div className={`flow-step ${selectedTicket.status === '已解决' ? 'done' : ''}`}><span>{selectedTicket.status === '已解决' ? <Check size={12} /> : '3'}</span><div><strong>确认并关闭</strong><small>{selectedTicket.status === '已解决' ? '已完成' : '等待处理完成'}</small></div></div>
                </div>
              </div>

              <div className="people-section"><div className="detail-section-title">参与人员 <button type="button" onClick={assignToMe}><Plus size={14} />添加</button></div><div className="person-line"><i className="requester-avatar">{initials(selectedTicket.requester)}</i><span><strong>{selectedTicket.requester}</strong><small>申请人 · {selectedTicket.requesterTeam}</small></span><button type="button" aria-label="联系申请人" onClick={() => notify(`已打开与${selectedTicket.requester}的对话`)}><MessageSquare size={15} /></button></div><div className="person-line"><i className={`person-avatar ${selectedTicket.assigneeInitials === '—' ? 'unassigned-avatar' : ''}`}>{selectedTicket.assigneeInitials}</i><span><strong>{selectedTicket.assignee}</strong><small>当前处理人</small></span><button type="button" aria-label="指派给我" onClick={assignToMe}><Plus size={15} /></button></div></div>

              <div className="description-section"><div className="detail-section-title">问题描述</div><p>{selectedTicket.description}</p><button className="attachment-row" type="button" onClick={() => notify('暂无附件')}><Paperclip size={14} /><span>附件</span><small>0</small><ChevronRight size={14} /></button></div>

              <div className="detail-activity"><div className="detail-section-title">最近动态 <button type="button" onClick={() => notify('已显示全部动态')}>查看全部</button></div><div className="activity-line"><i><MessageSquare size={12} /></i><p><strong>周启明</strong> 添加了内部备注<small>8 分钟前</small></p></div><div className="activity-line"><i><Inbox size={12} /></i><p>工单已分配给 <strong>{selectedTicket.assignee}</strong><small>12 分钟前</small></p></div></div>

              <div className="detail-actions"><button className="secondary-action" type="button" onClick={selectedTicket.status === '处理中' ? waitForCustomer : assignToMe}>{selectedTicket.status === '处理中' ? <Clock3 size={15} /> : <Users size={15} />}{selectedTicket.status === '处理中' ? '等待客户' : '指派给我'}</button><button className="primary-action" type="button" onClick={moveTicketForward}>{selectedTicket.status === '已解决' ? <CheckCircle2 size={15} /> : <ArrowRight size={15} />}{selectedTicket.status === '已解决' ? '已完成' : selectedTicket.status === '等待客户' ? '恢复处理中' : selectedTicket.status === '处理中' ? '标记为已解决' : '开始处理'}</button></div>
            </> : <div className="detail-empty"><Inbox size={25} /><strong>选择一张工单</strong><span>查看流转进度与处理记录</span><button type="button" onClick={() => setSelectedId(tickets[0]?.id ?? '')}>打开最新工单</button></div>}
          </aside>
        </div>
      </main>

      {isCreateOpen && <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setIsCreateOpen(false); }}>
        <section className="create-modal" role="dialog" aria-modal="true" aria-labelledby="create-ticket-title">
          <div className="modal-heading"><div><span className="modal-icon"><LifeBuoy size={17} /></span><div><h2 id="create-ticket-title">新建工单</h2><p>描述需要协助的问题，我们会尽快跟进。</p></div></div><button className="icon-button" type="button" aria-label="关闭" onClick={() => setIsCreateOpen(false)}><X size={18} /></button></div>
          <form onSubmit={createTicket}>
            <label>问题主题<input autoFocus required maxLength={100} value={title} onChange={event => setTitle(event.target.value)} placeholder="简要描述你遇到的问题" /></label>
            <div className="modal-fields"><label>问题分类<select value={category} onChange={event => setCategory(event.target.value)}><option>产品与功能</option><option>账户与权限</option><option>数据问题</option><option>流程审批</option><option>其他问题</option></select></label><label>优先级<select value={priority} onChange={event => setPriority(event.target.value as TicketPriority)}><option>低</option><option>普通</option><option>高</option><option>紧急</option></select></label></div>
            <label>问题描述<textarea required rows={4} maxLength={1200} value={description} onChange={event => setDescription(event.target.value)} placeholder="补充问题发生的场景、影响范围和已尝试的操作..." /></label>
            <div className="modal-footer"><span><ShieldCheck size={14} />仅工作区成员可见</span><div><button className="cancel-action" type="button" onClick={() => setIsCreateOpen(false)}>取消</button><button className="create-ticket-button" type="submit"><Plus size={15} />提交工单</button></div></div>
          </form>
        </section>
      </div>}

      {toast && <div className="ticket-toast" role="status"><CheckCircle2 size={17} />{toast}</div>}
      <span className="sr-only"><Clock3 aria-hidden="true" />工单流转演示界面</span>
    </div>
  );
}

export default TicketFlowPage;

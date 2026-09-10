/* Admin service contracts. Set BOOKHUB_DATA_SOURCE to api when backend endpoints are available. */
(function () {
  const dataSource = window.BOOKHUB_DATA_SOURCE || 'api';
  const clone = value => JSON.parse(JSON.stringify(value));
  const now = '2026-09-10T09:00:00Z';

  const state = {
    disputes: [{
      id: 'DSP-1001', orderId: '#BH-10479', buyerId: 'USR-12', sellerId: 'SEL-03',
      buyer: 'Le Hoai Phuong', seller: 'Alpha Books', reason: 'San pham khong dung mo ta',
      description: 'Bia sach bi hu hong khi nhan hang.', amount: 890000, status: 'UNDER_REVIEW',
      evidence: [{ id: 'E-1', fileName: 'anh-bia-sach.jpg', mimeType: 'image/jpeg', fileUrl: '', uploadedAt: now }],
      buyerResponse: 'De nghi hoan tien mot phan.', sellerResponse: 'Seller dang cho phan hoi.',
      adminDecision: '', resolutionNote: '', createdAt: now, updatedAt: now, resolvedAt: null,
      timeline: [{ label: 'Khieu nai duoc tao', at: now }, { label: 'Admin dang xem xet', at: now }]
    }],
    payouts: [{
      id: 'PAY-2001', sellerId: 'SEL-01', seller: 'NXB Kim Dong', amount: 4500000,
      availableBalance: 8900000, bankAccountId: 'BANK-01', bankName: 'Vietcombank',
      accountName: 'CONG TY KIM DONG', accountNumberMasked: '**** **** 1234', status: 'PENDING',
      requestedAt: now, processedAt: null, rejectionReason: '', transactionId: null,
      relatedOrders: ['#BH-10471', '#BH-10462'], history: [{ label: 'Yeu cau duoc tao', at: now }]
    }],
    documents: [{ id: 'DOC-01', ownerId: 'SEL-01', type: 'BUSINESS_LICENSE', fileName: 'gpkd-kim-dong.pdf', mimeType: 'application/pdf', fileUrl: '', uploadedAt: now, status: 'NOT_CONNECTED' }],
    roles: [
      { id: 'SUPER_ADMIN', label: 'Super Admin', permissions: ['users.view', 'users.create', 'users.edit', 'users.delete', 'orders.view', 'orders.edit', 'orders.refund', 'products.view', 'products.approve', 'products.reject', 'products.edit', 'sellers.view', 'sellers.approve', 'sellers.reject', 'sellers.suspend', 'finance.view', 'payouts.view', 'payouts.approve', 'payouts.reject', 'disputes.view', 'disputes.resolve', 'marketing.view', 'marketing.manage', 'settings.view', 'settings.manage'] },
      { id: 'ADMIN', label: 'Admin', permissions: ['users.view', 'users.edit', 'orders.view', 'orders.edit', 'products.view', 'products.approve', 'products.reject', 'sellers.view', 'sellers.approve', 'sellers.reject', 'finance.view', 'payouts.view', 'disputes.view', 'disputes.resolve', 'marketing.view', 'settings.view'] },
      { id: 'MODERATOR', label: 'Moderator', permissions: ['orders.view', 'products.view', 'products.approve', 'products.reject', 'sellers.view', 'disputes.view'] },
      { id: 'FINANCE', label: 'Finance', permissions: ['orders.view', 'finance.view', 'payouts.view', 'payouts.approve', 'payouts.reject'] },
      { id: 'SUPPORT', label: 'Customer Support', permissions: ['users.view', 'orders.view', 'disputes.view'] },
      { id: 'MARKETING', label: 'Marketing', permissions: ['marketing.view', 'marketing.manage'] }
    ],
    auditLogs: []
  };

  function apiRequest(path, options = {}) {
    return window.apiCall(path, options);
  }
  function useApi(path, options) {
    if (dataSource !== 'api') return null;
    return apiRequest(path, options);
  }
  function recordAudit(action, targetType, targetId, metadata = {}) {
    const entry = { id: `AUD-${Date.now()}`, actorId: window.state?.currentUser?.id || 'admin', action, targetType, targetId, metadata, createdAt: new Date().toISOString() };
    state.auditLogs.unshift(entry);
    return Promise.resolve(clone(entry));
  }
  function find(collection, id) { return collection.find(item => String(item.id) === String(id)); }
  function rejectReason(reason) { if (!reason || !reason.trim()) throw new Error('Vui long nhap ly do.'); }

  const mockOrApi = (apiPath, mockValue, options) => useApi(apiPath, options) || Promise.resolve(clone(mockValue));
  const mapDispute = item => item ? ({ ...item, buyer: item.buyer || `User #${item.buyer_id}`, seller: item.seller || `Seller #${item.seller_id}`, orderId: item.orderId || `Order #${item.order_id}`, buyerResponse: item.buyerResponse || item.buyer_response, sellerResponse: item.sellerResponse || item.seller_response, adminDecision: item.adminDecision || item.admin_decision, resolutionNote: item.resolutionNote || item.resolution_note, createdAt: item.createdAt || item.created_at, updatedAt: item.updatedAt || item.updated_at, resolvedAt: item.resolvedAt || item.resolved_at, timeline: item.timeline || [] }) : item;
  const mapPayout = item => item ? ({ ...item, seller: item.seller || `Seller #${item.seller_id}`, bankName: item.bankName || item.bank_name, accountName: item.accountName || item.bank_account_holder, accountNumberMasked: item.accountNumberMasked || (item.bank_account_number ? `**** ${item.bank_account_number.slice(-4)}` : '****'), requestedAt: item.requestedAt || item.created_at, processedAt: item.processedAt || item.processed_at, rejectionReason: item.rejectionReason || item.rejection_reason }) : item;
  const DisputeService = {
    getDisputes: () => (useApi('/api/admin/disputes') || Promise.resolve(state.disputes)).then(items => items.map(mapDispute)),
    getDispute: id => (useApi(`/api/admin/disputes/${id}`) || Promise.resolve(find(state.disputes, id))).then(mapDispute),
    updateDisputeStatus: (id, status) => { const item = find(state.disputes, id); if (item) item.status = status; return recordAudit('UPDATE_DISPUTE_STATUS', 'DISPUTE', id, { status }).then(() => clone(item)); },
    requestSellerResponse: id => useApi(`/api/admin/disputes/${id}/request-seller-response`, { method: 'POST' }) || (() => { const item = find(state.disputes, id); if (item) item.status = 'WAITING_SELLER'; return recordAudit('REQUEST_SELLER_RESPONSE', 'DISPUTE', id).then(() => clone(item)); })(),
    resolveDispute: (id, decision, note) => useApi(`/api/admin/disputes/${id}/resolve`, { method: 'POST', body: JSON.stringify({ decision, note }) }) || (() => { const item = find(state.disputes, id); if (item) Object.assign(item, { status: 'RESOLVED', adminDecision: decision, resolutionNote: note || '', resolvedAt: new Date().toISOString() }); return recordAudit('RESOLVE_DISPUTE', 'DISPUTE', id, { decision, note }).then(() => clone(item)); })(),
    rejectDispute: (id, reason) => { rejectReason(reason); return useApi(`/api/admin/disputes/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }) || (() => { const item = find(state.disputes, id); if (item) Object.assign(item, { status: 'REJECTED', resolutionNote: reason, resolvedAt: new Date().toISOString() }); return recordAudit('REJECT_DISPUTE', 'DISPUTE', id, { reason }).then(() => clone(item)); })(); }
  };
  const PayoutService = {
    getPayoutRequests: () => (useApi('/api/admin/payouts') || Promise.resolve(state.payouts)).then(items => items.map(mapPayout)),
    getPayout: id => (useApi(`/api/admin/payouts/${id}`) || Promise.resolve(find(state.payouts, id))).then(mapPayout),
    approvePayout: id => useApi(`/api/admin/payouts/${id}/approve`, { method: 'POST' }) || (() => { const item = find(state.payouts, id); if (!item || item.status !== 'PENDING') return Promise.reject(new Error('Chi co yeu cau PENDING moi duoc duyet.')); item.status = 'APPROVED'; item.processedAt = new Date().toISOString(); return recordAudit('APPROVE_PAYOUT', 'PAYOUT', id).then(() => clone(item)); })(),
    rejectPayout: (id, reason) => { rejectReason(reason); return useApi(`/api/admin/payouts/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }) || (() => { const item = find(state.payouts, id); if (!item || item.status !== 'PENDING') return Promise.reject(new Error('Yeu cau khong con o trang thai cho duyet.')); Object.assign(item, { status: 'REJECTED', rejectionReason: reason, processedAt: new Date().toISOString() }); return recordAudit('REJECT_PAYOUT', 'PAYOUT', id, { reason }).then(() => clone(item)); })(); }
  };
  const DocumentService = {
    getDocument: id => mockOrApi(`/api/admin/documents/${id}`, find(state.documents, id)),
    getDocumentPreview: id => (useApi(`/api/admin/documents/${id}/preview`) || Promise.resolve(null)).then(result => { if (result) return { ...result.document, available: result.available, fileUrl: result.file_url, message: result.message || '' }; const doc = find(state.documents, id) || { id, type: 'OTHER', fileName: 'Tài liệu chưa đồng bộ', mimeType: 'application/octet-stream', fileUrl: '', uploadedAt: now, status: 'NOT_CONNECTED' }; return { ...clone(doc), available: Boolean(doc.fileUrl), message: doc.fileUrl ? '' : 'Document preview chua duoc ket noi voi storage backend.' }; }),
    downloadDocument: id => { if (dataSource === 'api') { window.open(`/api/admin/documents/${id}/download`, '_blank', 'noopener'); return Promise.resolve({ id }); } const doc = find(state.documents, id); if (!doc?.fileUrl) return Promise.reject(new Error('Document preview chua duoc ket noi voi storage backend.')); window.open(doc.fileUrl, '_blank', 'noopener'); return Promise.resolve(doc); }
  };
  const PermissionService = {
    getRoles: () => mockOrApi('/api/admin/roles', state.roles),
    getPermissions: () => Promise.resolve([...new Set(state.roles.flatMap(role => role.permissions))].sort()),
    updateRolePermissions: (id, permissions) => { const role = find(state.roles, id); if (role) role.permissions = [...permissions]; return recordAudit('CHANGE_PERMISSION', 'ROLE', id, { permissions }).then(() => clone(role)); },
    can: (roleId, permission) => Boolean(find(state.roles, roleId)?.permissions.includes(permission))
  };
  const ProductService = {
    approveProduct: id => apiRequest(`/api/admin/books/${id}/approve`, { method: 'POST' }).then(result => recordAudit('APPROVE_PRODUCT', 'PRODUCT', id).then(() => result)),
    rejectProduct: (id, reason) => apiRequest(`/api/admin/books/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }).then(result => recordAudit('REJECT_PRODUCT', 'PRODUCT', id, { reason }).then(() => result)),
    getProduct: id => apiRequest(`/api/admin/books/${id}`)
  };
  const SellerService = {
    approveSeller: id => apiRequest(`/api/admin/sellers/${id}/approve`, { method: 'POST' }).then(result => recordAudit('APPROVE_SELLER', 'SELLER', id).then(() => result)),
    rejectSeller: (id, reason) => apiRequest(`/api/admin/sellers/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }).then(result => recordAudit('REJECT_SELLER', 'SELLER', id, { reason }).then(() => result)),
    getSeller: id => apiRequest(`/api/admin/sellers/${id}`)
  };
  const UserService = {
    toggleUser: id => apiRequest(`/api/admin/users/${id}/toggle-ban`, { method: 'POST' }).then(result => recordAudit(result.current_status === 'BANNED' ? 'SUSPEND_USER' : 'UNSUSPEND_USER', 'USER', id).then(() => result)),
    getUser: id => apiRequest('/api/admin/users').then(items => find(items, id))
  };
  const AuditLogService = { list: () => Promise.resolve(clone(state.auditLogs)), record: recordAudit };

  window.AdminServices = { dataSource, DisputeService, PayoutService, DocumentService, PermissionService, ProductService, SellerService, UserService, AuditLogService, state };
})();

document.addEventListener('DOMContentLoaded', () => {
  const isEnglish = document.documentElement.lang === 'en';
  const links = document.querySelectorAll('[data-transition-link]');
  const addModal = document.querySelector('#addTransactionModal');
  const addModalOpenButtons = document.querySelectorAll('[data-open-add-modal]');
  const addModalCloseButtons = document.querySelectorAll('[data-close-modal]');
  const addModalAmountInput = document.querySelector('#addTxAmount');
  const detailModal = document.querySelector('#transactionDetailModal');
  const detailModalCloseButtons = document.querySelectorAll('[data-close-detail-modal]');
  const detailModalOpenButtons = document.querySelectorAll('[data-open-detail-modal]');

  const txDetailBadge = document.querySelector('#txDetailBadge');
  const txDetailCategory = document.querySelector('#txDetailCategory');
  const txDetailNote = document.querySelector('#txDetailNote');
  const txDetailDate = document.querySelector('#txDetailDate');
  const txDetailAmount = document.querySelector('#txDetailAmount');
  const txDetailType = document.querySelector('#txDetailType');
  const txDetailId = document.querySelector('#txDetailId');
  const txDetailEditLink = document.querySelector('#txDetailEditLink');
  const txDetailDeleteForm = document.querySelector('#txDetailDeleteForm');
  const searchInput = document.querySelector('#transactionSearch');
  const tableRows = document.querySelectorAll('#transactionTableBody tr[data-search]');
  const emptyRow = document.querySelector('#transactionTableBody .empty-row');

  links.forEach((link) => {
    link.addEventListener('click', (event) => {
      const href = link.getAttribute('href');

      if (!href || href.startsWith('#')) {
        return;
      }

      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }

      event.preventDefault();
      window.location.href = href;
    });
  });

  if (addModal) {
    const setModalOpen = (open) => {
      addModal.classList.toggle('is-open', open);
      addModal.setAttribute('aria-hidden', open ? 'false' : 'true');
      document.body.classList.toggle('modal-open', open);

      if (open && addModalAmountInput) {
        addModalAmountInput.focus();
      }
    };

    addModalOpenButtons.forEach((button) => {
      button.addEventListener('click', () => setModalOpen(true));
    });

    addModalCloseButtons.forEach((button) => {
      button.addEventListener('click', () => setModalOpen(false));
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && addModal.classList.contains('is-open')) {
        setModalOpen(false);
      }
    });

    if (window.location.search.includes('open_add=1') || window.location.search.includes('open_add=true')) {
      setModalOpen(true);
    }
  }

  if (detailModal) {
    const setDetailOpen = (open) => {
      detailModal.classList.toggle('is-open', open);
      detailModal.setAttribute('aria-hidden', open ? 'false' : 'true');
      document.body.classList.toggle('modal-open', open);
    };

    const fillDetail = (row) => {
      if (!row) {
        return;
      }

      const amount = Number(row.dataset.transactionAmount || '0');
      const amountDisplay = row.dataset.transactionAmountDisplay || '0 VND';
      const kind = row.dataset.transactionKind || '-';
      const editUrl = row.dataset.transactionEditUrl || '#';
      const deleteUrl = row.dataset.transactionDeleteUrl || '#';

      if (txDetailBadge) {
        txDetailBadge.textContent = kind;
        txDetailBadge.className = `detail-badge ${amount >= 0 ? 'income' : 'expense'}`;
      }
      if (txDetailCategory) {
        txDetailCategory.textContent = row.dataset.transactionCategory || (isEnglish ? 'Unknown' : 'Không xác định');
      }
      if (txDetailNote) {
        txDetailNote.textContent = row.dataset.transactionNote || (isEnglish ? 'No note' : 'Không có ghi chú');
      }
      if (txDetailDate) {
        txDetailDate.textContent = row.dataset.transactionDate || '-';
      }
      if (txDetailAmount) {
        txDetailAmount.textContent = `${amount >= 0 ? '+' : '-'}${amountDisplay}`;
        txDetailAmount.className = amount >= 0 ? 'income' : 'expense';
      }
      if (txDetailType) {
        txDetailType.textContent = kind;
      }
      if (txDetailId) {
        txDetailId.textContent = `#${row.dataset.transactionId || ''}`;
      }
      if (txDetailEditLink) {
        txDetailEditLink.setAttribute('href', editUrl);
      }
      if (txDetailDeleteForm) {
        txDetailDeleteForm.setAttribute('action', deleteUrl);
      }
    };

    detailModalOpenButtons.forEach((button) => {
      button.addEventListener('click', () => {
        const row = button.closest('tr');
        fillDetail(row);
        setDetailOpen(true);
      });
    });

    detailModalCloseButtons.forEach((button) => {
      button.addEventListener('click', () => setDetailOpen(false));
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && detailModal.classList.contains('is-open')) {
        setDetailOpen(false);
      }
    });
  }

  if (searchInput && tableRows.length) {
    const filterRows = () => {
      const query = searchInput.value.trim().toLowerCase();
      let visibleCount = 0;

      tableRows.forEach((row) => {
        const haystack = row.getAttribute('data-search') || '';
        const visible = !query || haystack.toLowerCase().includes(query);
        row.style.display = visible ? '' : 'none';
        if (visible) {
          visibleCount += 1;
        }
      });

      if (emptyRow) {
        emptyRow.style.display = visibleCount > 0 ? 'none' : '';
      }
    };

    searchInput.addEventListener('input', filterRows);
    filterRows();
  }
});
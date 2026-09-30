(function (root, factory) {
    var archive = factory();
    if (typeof module === 'object' && module.exports) {
        module.exports = archive;
    } else {
        root.CatalogBillArchive = archive;
    }
}(typeof globalThis === 'object' ? globalThis : this, function () {
    'use strict';

    var DATABASE_NAME = 'skumar-generated-bills';
    var DATABASE_VERSION = 1;
    var DIRECTORY_KEY = 'generatedBillsDirectory';
    var BILL_STORE = 'bills';

    function monthFor(date) {
        var year = date.getFullYear();
        var month = String(date.getMonth() + 1);
        if (month.length < 2) month = '0' + month;
        return year + '-' + month;
    }

    function safeFileName(reference) {
        var name = String(reference || '').replace(/[^a-zA-Z0-9_-]/g, '');
        if (!name) throw new Error('The bill reference is invalid.');
        return name + '.html';
    }

    function extractBillMeta(html) {
        var buyerName = 'Cash customer';
        var grandTotal = '';
        var billDate = '';
        if (!html || typeof html !== 'string') {
            return { buyerName: buyerName, grandTotal: grandTotal, billDate: billDate };
        }
        var buyerMatch = html.match(/id=["']pBuyerName["'][^>]*>([^<]+)</i);
        if (buyerMatch && buyerMatch[1].trim()) {
            buyerName = buyerMatch[1].trim();
        }
        var totalMatch = html.match(/id=["']pGrandTotal["'][^>]*>([^<]+)</i) ||
                         html.match(/class=["'][^"']*grand-total[^"']*["'][^>]*>.*?(?:₹|INR|\b)([\d,]+(?:\.\d{2})?)/is);
        if (totalMatch && totalMatch[1].trim()) {
            grandTotal = totalMatch[1].trim();
        }
        var dateMatch = html.match(/id=["']pDate["'][^>]*>([^<]+)</i);
        if (dateMatch && dateMatch[1].trim()) {
            billDate = dateMatch[1].trim();
        }
        return { buyerName: buyerName, grandTotal: grandTotal, billDate: billDate };
    }

    function readEntries(directory) {
        var iterator = directory.entries();
        var entries = [];
        function readNext() {
            return iterator.next().then(function (result) {
                if (result.done) return entries;
                entries.push(result.value);
                return readNext();
            });
        }
        return readNext();
    }

    function BillArchive(options) {
        this.window = options.window;
        this.storage = options.storage || new IndexedDbStorage(options.indexedDB);
        this.directoryHandle = null;
    }

    BillArchive.prototype.restoreDirectory = function () {
        var self = this;
        return this.storage.getDirectory().then(function (handle) {
            if (!handle) return false;
            self.directoryHandle = handle;
            return true;
        });
    };

    BillArchive.prototype.saveToLocalStorage = function (entry) {
        if (!this.window || !this.window.localStorage) return;
        try {
            var raw = this.window.localStorage.getItem('skumar_saved_bills_v1');
            var list = raw ? JSON.parse(raw) : [];
            list = list.filter(function (item) { return item.id !== entry.id; });
            list.unshift(entry);
            if (list.length > 200) list = list.slice(0, 200);
            this.window.localStorage.setItem('skumar_saved_bills_v1', JSON.stringify(list));
        } catch (e) {
            // LocalStorage might be full or private mode
        }
    };

    BillArchive.prototype.loadFromLocalStorage = function () {
        if (!this.window || !this.window.localStorage) return [];
        try {
            var raw = this.window.localStorage.getItem('skumar_saved_bills_v1');
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    };

    BillArchive.prototype.loadInjectedBills = function () {
        if (this.window && Array.isArray(this.window.INJECTED_SAVED_BILLS)) {
            return this.window.INJECTED_SAVED_BILLS;
        }
        return [];
    };

    BillArchive.prototype.selectDirectory = function () {
        var self = this;
        if (typeof this.window.showDirectoryPicker !== 'function') {
            throw new Error('This browser cannot write to a selected folder. Bills will be downloaded and kept in the browser archive.');
        }
        var selection = this.window.showDirectoryPicker({
            id: 'skumar-generated-bills',
            mode: 'readwrite'
        });
        return Promise.resolve(selection).then(function (handle) {
            if (handle.name !== 'data' && handle.name !== 'generated_bills') {
                throw new Error('Select the data folder or generated_bills folder so monthly bill folders are created in the requested location.');
            }
            self.directoryHandle = handle;
            return self.storage.setDirectory(handle).then(function () {
                return handle;
            });
        });
    };

    BillArchive.prototype.saveBill = function (bill) {
        var self = this;
        var month = monthFor(bill.date);
        var fileName = safeFileName(bill.reference);
        var handle = this.directoryHandle;
        var directoryPromise;
        if (!handle && typeof this.window.showDirectoryPicker === 'function') {
            directoryPromise = this.selectDirectory().catch(function (error) {
                if (error && error.name === 'AbortError') {
                    return null;
                }
                throw error;
            });
        } else {
            directoryPromise = Promise.resolve(handle);
        }

        return directoryPromise.then(function (selectedHandle) {
            var meta = extractBillMeta(bill.html);
            var entry = {
                id: month + '/' + fileName,
                month: month,
                fileName: fileName,
                reference: bill.reference,
                buyerName: meta.buyerName,
                grandTotal: meta.grandTotal,
                billDate: meta.billDate,
                savedAt: bill.date.toISOString(),
                html: bill.html,
                storage: selectedHandle ? 'folder' : 'browser'
            };

            // Always sync to localStorage
            self.saveToLocalStorage(entry);

            if (!selectedHandle) {
                return self.storage.saveBill(entry).then(function () {
                    self.downloadBill(fileName, bill.html);
                    return { storage: 'browser', entry: entry };
                }, function (error) {
                    self.downloadBill(fileName, bill.html);
                    entry.archiveWarning = error.message || 'Unable to keep a browser archive copy.';
                    return { storage: 'download', entry: entry };
                });
            }

            return Promise.resolve(selectedHandle.queryPermission({ mode: 'readwrite' }))
                .then(function (permission) {
                    if (permission === 'granted') return permission;
                    return selectedHandle.requestPermission({ mode: 'readwrite' });
                })
                .then(function (permission) {
                    if (permission !== 'granted') {
                        throw new Error('Folder access was not granted. The bill was not written to generated_bills.');
                    }
                    if (selectedHandle.name === 'generated_bills') {
                        return selectedHandle;
                    }
                    return selectedHandle.getDirectoryHandle('generated_bills', { create: true });
                })
                .then(function (genBillsDir) {
                    return genBillsDir.getDirectoryHandle(month, { create: true });
                })
                .then(function (monthDirectory) {
                    return monthDirectory.getFileHandle(fileName, { create: true });
                })
                .then(function (file) {
                    return file.createWritable().then(function (writable) {
                        return writable.write(bill.html).then(function () {
                            return writable.close();
                        });
                    });
                })
                .then(function () {
                    return self.storage.saveBill(entry).then(function () {
                        return { storage: 'folder', entry: entry };
                    }, function (error) {
                        entry.archiveWarning = error.message || 'Unable to update the browser bill index.';
                        return { storage: 'folder', entry: entry };
                    });
                });
        });
    };

    BillArchive.prototype.listBills = function () {
        var self = this;
        return this.storage.listBills().then(function (cached) {
            var entries = new Map();

            // 1. Injected bills from server / disk
            self.loadInjectedBills().forEach(function (bill) {
                var meta = extractBillMeta(bill.html);
                entries.set(bill.id, Object.assign({
                    buyerName: meta.buyerName,
                    grandTotal: meta.grandTotal,
                    billDate: meta.billDate
                }, bill));
            });

            // 2. LocalStorage bills
            self.loadFromLocalStorage().forEach(function (bill) {
                var meta = extractBillMeta(bill.html);
                entries.set(bill.id, Object.assign({
                    buyerName: meta.buyerName,
                    grandTotal: meta.grandTotal,
                    billDate: meta.billDate
                }, bill));
            });

            // 3. Cached indexedDB bills
            cached.forEach(function (entry) {
                var meta = extractBillMeta(entry.html);
                entries.set(entry.id, Object.assign({
                    buyerName: meta.buyerName,
                    grandTotal: meta.grandTotal,
                    billDate: meta.billDate
                }, entry));
            });

            if (!self.directoryHandle) return Array.from(entries.values()).sort(sortBills);

            return Promise.resolve(self.directoryHandle.queryPermission({ mode: 'read' }))
                .then(function (permission) {
                    if (permission !== 'granted') return Array.from(entries.values()).sort(sortBills);
                    cached.forEach(function (entry) {
                        if (entry.storage === 'folder') entries.delete(entry.id);
                    });
                    var getGenBills = self.directoryHandle.name === 'generated_bills'
                        ? Promise.resolve(self.directoryHandle)
                        : self.directoryHandle.getDirectoryHandle('generated_bills').catch(function() { return null; });

                    return getGenBills.then(function(genBillsDir) {
                        if (!genBillsDir) return [];
                        return readEntries(genBillsDir);
                    }).then(function (months) {
                        return months.reduce(function (chain, monthEntry) {
                            var month = monthEntry[0];
                            var monthHandle = monthEntry[1];
                            if (!/^\d{4}-\d{2}$/.test(month) || monthHandle.kind !== 'directory') {
                                return chain;
                            }
                            return chain.then(function () {
                                return readEntries(monthHandle).then(function (files) {
                                    return files.reduce(function (fileChain, fileEntry) {
                                        var fileName = fileEntry[0];
                                        var fileHandle = fileEntry[1];
                                        if (!/^[a-zA-Z0-9_-]+\.html$/i.test(fileName)
                                            || fileHandle.kind !== 'file') {
                                            return fileChain;
                                        }
                                        return fileChain.then(function () {
                                            return fileHandle.getFile().then(function (file) {
                                                var id = month + '/' + fileName;
                                                return file.text().then(function (html) {
                                                    var meta = extractBillMeta(html);
                                                    entries.set(id, {
                                                        id: id,
                                                        month: month,
                                                        fileName: fileName,
                                                        reference: fileName.slice(0, -5),
                                                        buyerName: meta.buyerName,
                                                        grandTotal: meta.grandTotal,
                                                        billDate: meta.billDate,
                                                        savedAt: new Date(file.lastModified).toISOString(),
                                                        html: html,
                                                        storage: 'folder'
                                                    });
                                                });
                                            });
                                        });
                                    }, Promise.resolve());
                                });
                            });
                        }, Promise.resolve()).then(function () {
                            return Array.from(entries.values()).sort(sortBills);
                        });
                    });
                });
        });
    };

    BillArchive.prototype.openBill = function (entry, autoPrint) {
        var html = entry.html;
        if (autoPrint) {
            html = html.replace('</body>', '<script>window.addEventListener("load", function() { setTimeout(function() { window.print(); }, 400); });<\/script></body>');
        }
        var blob = new this.window.Blob([html], { type: 'text/html;charset=utf-8' });
        var url = this.window.URL.createObjectURL(blob);
        var win = this.window.open(url, '_blank');
        if (!win || win.closed || typeof win.closed === 'undefined') {
            var link = this.window.document.createElement('a');
            link.href = url;
            link.target = '_blank';
            link.rel = 'noopener';
            if (this.window.document && this.window.document.body) {
                this.window.document.body.appendChild(link);
                link.click();
                this.window.document.body.removeChild(link);
            } else {
                link.click();
            }
        }
        this.window.setTimeout(function () {
            this.window.URL.revokeObjectURL(url);
        }.bind(this), 120000);
    };

    BillArchive.prototype.downloadBill = function (fileName, html) {
        var url = this.window.URL.createObjectURL(
            new this.window.Blob([html], { type: 'text/html;charset=utf-8' })
        );
        var link = this.window.document.createElement('a');
        link.href = url;
        link.download = fileName;
        link.click();
        this.window.setTimeout(function () {
            this.window.URL.revokeObjectURL(url);
        }.bind(this), 1000);
    };

    function sortBills(left, right) {
        return right.month.localeCompare(left.month)
            || right.fileName.localeCompare(left.fileName);
    }

    function IndexedDbStorage(indexedDB) {
        this.indexedDB = indexedDB;
        this.database = null;
    }

    IndexedDbStorage.prototype.open = function () {
        var self = this;
        if (this.database) return Promise.resolve(this.database);
        if (!this.indexedDB) {
            return Promise.reject(new Error('This browser does not support the local bill archive.'));
        }
        return new Promise(function (resolve, reject) {
            var request = self.indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
            request.onupgradeneeded = function () {
                var database = request.result;
                if (!database.objectStoreNames.contains('settings')) {
                    database.createObjectStore('settings', { keyPath: 'key' });
                }
                if (!database.objectStoreNames.contains(BILL_STORE)) {
                    database.createObjectStore(BILL_STORE, { keyPath: 'id' });
                }
            };
            request.onsuccess = function () {
                self.database = request.result;
                resolve(self.database);
            };
            request.onerror = function () {
                reject(request.error || new Error('Unable to open the local bill archive.'));
            };
        });
    };

    IndexedDbStorage.prototype.getDirectory = function () {
        return this.open().then(function (database) {
            return new Promise(function (resolve, reject) {
                var request = database.transaction('settings', 'readonly')
                    .objectStore('settings').get(DIRECTORY_KEY);
                request.onsuccess = function () {
                    resolve(request.result ? request.result.handle : null);
                };
                request.onerror = function () {
                    reject(request.error || new Error('Unable to restore the bills folder.'));
                };
            });
        });
    };

    IndexedDbStorage.prototype.setDirectory = function (handle) {
        return this.open().then(function (database) {
            return new Promise(function (resolve, reject) {
                var transaction = database.transaction('settings', 'readwrite');
                transaction.objectStore('settings').put({ key: DIRECTORY_KEY, handle: handle });
                transaction.oncomplete = resolve;
                transaction.onerror = function () {
                    reject(transaction.error || new Error('Unable to remember the bills folder.'));
                };
                transaction.onabort = function () {
                    reject(transaction.error || new Error('Unable to remember the bills folder.'));
                };
            });
        });
    };

    IndexedDbStorage.prototype.saveBill = function (entry) {
        return this.open().then(function (database) {
            return new Promise(function (resolve, reject) {
                var transaction = database.transaction(BILL_STORE, 'readwrite');
                transaction.objectStore(BILL_STORE).put(entry);
                transaction.oncomplete = resolve;
                transaction.onerror = function () {
                    reject(transaction.error || new Error('Unable to save the local bill archive.'));
                };
                transaction.onabort = function () {
                    reject(transaction.error || new Error('Unable to save the local bill archive.'));
                };
            });
        });
    };

    IndexedDbStorage.prototype.listBills = function () {
        return this.open().then(function (database) {
            return new Promise(function (resolve, reject) {
                var request = database.transaction(BILL_STORE, 'readonly')
                    .objectStore(BILL_STORE).getAll();
                request.onsuccess = function () { resolve(request.result || []); };
                request.onerror = function () {
                    reject(request.error || new Error('Unable to read the local bill archive.'));
                };
            });
        });
    };

    return {
        BillArchive: BillArchive,
        monthFor: monthFor,
        safeFileName: safeFileName
    };
}));

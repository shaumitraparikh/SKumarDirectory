'use strict';

const assert = require('assert');
const { BillArchive, monthFor, safeFileName } = require('../assets/js/bill_archive');

class MemoryStorage {
    constructor() {
        this.bills = new Map();
        this.directory = null;
    }

    getDirectory() { return Promise.resolve(this.directory); }
    setDirectory(handle) { this.directory = handle; return Promise.resolve(); }
    saveBill(entry) { this.bills.set(entry.id, entry); return Promise.resolve(); }
    listBills() { return Promise.resolve(Array.from(this.bills.values())); }
}

function makeDirectory(name) {
    const files = new Map();
    const directories = new Map();
    return {
        name,
        kind: 'directory',
        files,
        directories,
        queryPermission() { return Promise.resolve('granted'); },
        requestPermission() { return Promise.resolve('granted'); },
        getDirectoryHandle(month, options) {
            assert.strictEqual(options.create, true);
            if (!directories.has(month)) directories.set(month, makeDirectory(month));
            return Promise.resolve(directories.get(month));
        },
        getFileHandle(fileName, options) {
            assert.strictEqual(options.create, true);
            if (!files.has(fileName)) {
                const record = { content: '', lastModified: 0 };
                files.set(fileName, {
                    kind: 'file',
                    createWritable() {
                        return Promise.resolve({
                            write(content) { record.content = content; return Promise.resolve(); },
                            close() { record.lastModified = Date.now(); return Promise.resolve(); }
                        });
                    },
                    getFile() {
                        return Promise.resolve({
                            lastModified: record.lastModified,
                            text() { return Promise.resolve(record.content); }
                        });
                    }
                });
            }
            return Promise.resolve(files.get(fileName));
        },
        entries() {
            const values = Array.from(directories.entries()).concat(Array.from(files.entries()));
            let index = 0;
            return {
                next() {
                    if (index >= values.length) return Promise.resolve({ done: true });
                    return Promise.resolve({ done: false, value: values[index++] });
                }
            };
        }
    };
}

function run() {
    const date = new Date(2026, 8, 26, 12);
    assert.strictEqual(monthFor(date), '2026-09');
    assert.strictEqual(safeFileName('PI-20260926-000001'), 'PI-20260926-000001.html');
    assert.strictEqual(safeFileName('../invoice'), 'invoice.html');
    assert.throws(() => safeFileName('../../'), /reference is invalid/);

    const root = makeDirectory('generated_bills');
    const storage = new MemoryStorage();
    const archive = new BillArchive({
        storage,
        indexedDB: null,
        window: { showDirectoryPicker: () => Promise.resolve(root) }
    });
    const wrongFolderArchive = new BillArchive({
        storage: new MemoryStorage(),
        indexedDB: null,
        window: { showDirectoryPicker: () => Promise.resolve(makeDirectory('Documents')) }
    });
    return archive.saveBill({
        date,
        reference: 'PI-20260926-000001',
        html: '<!doctype html><p>test bill</p>'
    }).then(function (result) {
        assert.strictEqual(result.storage, 'folder');
        assert.ok(root.directories.has('2026-09'));
        assert.ok(root.directories.get('2026-09').files.has('PI-20260926-000001.html'));
        assert.strictEqual(storage.directory, root);
        return archive.saveBill({
            date: new Date(2026, 9, 2, 12),
            reference: 'PI-20261002-000001',
            html: '<p>October bill</p>'
        });
    }).then(function () {
        return archive.listBills();
    }).then(function (entries) {
        assert.strictEqual(entries.length, 2);
        assert.strictEqual(entries[0].month, '2026-10');
        assert.strictEqual(entries[0].id, '2026-10/PI-20261002-000001.html');
        assert.strictEqual(entries[1].id, '2026-09/PI-20260926-000001.html');
        assert.strictEqual(entries[1].html, '<!doctype html><p>test bill</p>');
        return wrongFolderArchive.saveBill({
            date,
            reference: 'PI-20260926-000002',
            html: '<p>not saved</p>'
        }).then(function () {
            throw new Error('A differently named folder should not be accepted.');
        }, function (error) {
            assert.ok(/Select the generated_bills folder/.test(error.message));
        });
    }).then(function () {

    let downloadedName = '';
    const fallbackStorage = new MemoryStorage();
    const fallbackArchive = new BillArchive({
        storage: fallbackStorage,
        indexedDB: null,
        window: {
            Blob: function (parts) { this.parts = parts; },
            URL: {
                createObjectURL() { return 'blob:test-bill'; },
                revokeObjectURL() {}
            },
            setTimeout() {},
            document: {
                createElement() {
                    return {
                        click() { downloadedName = this.download; }
                    };
                }
            }
        }
    });
    return fallbackArchive.saveBill({
        date,
        reference: 'PI-20260926-000003',
        html: '<p>browser fallback</p>'
    }).then(function (fallbackResult) {
        assert.strictEqual(fallbackResult.storage, 'browser');
        assert.strictEqual(downloadedName, 'PI-20260926-000003.html');
        return fallbackArchive.listBills();
    }).then(function (entries) {
        assert.strictEqual(entries.length, 1);
        console.log('PASS: bill archive paths, monthly grouping, folder writes, listing, and folder validation.');
    });
    });
}

run().catch(error => {
    console.error(error);
    process.exitCode = 1;
});

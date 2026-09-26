'use strict';

const assert = require('assert');
const directory = require('../assets/js/client_directory_core');

const csv = '\uFEFFclient_id,name,business_name,phone,email,address,state,pincode,gstin\r\n'
    + 'C001,"Asha ""Ace"" Shah",Ace Electricals,9869905779,asha@example.in,'
    + '"12, Market Road",Maharashtra,400002,27ACJPP2955J1Z4\r\n'
    + ',,,,,,,,\r\n'
    + 'C002,,,,,,,,\r\n';
const customers = directory.parseCsv(csv);

assert.strictEqual(customers.length, 2);
assert.strictEqual(customers[0].name, 'Asha "Ace" Shah');
assert.strictEqual(customers[0].address, '12, Market Road');
assert.strictEqual(customers[0].gstin, '27ACJPP2955J1Z4');
assert.strictEqual(customers[1].name, 'C002');
assert.strictEqual(
    directory.findCustomer(customers, 'Asha "Ace" Shah · Ace Electricals · 9869905779'),
    customers[0]
);
assert.strictEqual(directory.findCustomer(customers, 'not a customer'), null);
assert.deepStrictEqual(directory.parseCsv(
    'customer name,company,mobile,delivery address,state,pin code\n'
    + 'Ravi Kumar,RK Supplies,9821361314,5 Main St,Maharashtra,400001'
), [{
    name: 'Ravi Kumar',
    business_name: 'RK Supplies',
    phone: '9821361314',
    address: '5 Main St',
    state: 'Maharashtra',
    pincode: '400001'
}]);
assert.throws(() => directory.parseCsv('name,address\n"unfinished,road'), /unclosed quoted field/);

console.log('PASS: customer CSV parsing, safe display labels, lookup, and aliases.');

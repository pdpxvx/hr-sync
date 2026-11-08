/**
 * Recalcula Active_Placements__c dels comptes afectats.
 * "Bulkified": una sola consulta i una sola DML, tant si arriben 1 com 2.000 registres
 * (la sincronització fa servir la Bulk API, així que els lots grans són el cas normal).
 */
public with sharing class PlacementTriggerHandler {

    public static void recalculateActivePlacements(List<Placement__c> newList, List<Placement__c> oldList) {
        Set<Id> accountIds = new Set<Id>();
        collectAccountIds(newList, accountIds);
        collectAccountIds(oldList, accountIds); // un contracte pot haver canviat de client
        if (accountIds.isEmpty()) {
            return;
        }

        Map<Id, Integer> counts = new Map<Id, Integer>();
        for (Id accountId : accountIds) {
            counts.put(accountId, 0);
        }
        for (AggregateResult ar : [
            SELECT Account__c accountId, COUNT(Id) total
            FROM Placement__c
            WHERE Account__c IN :accountIds AND Status__c = 'Active'
            GROUP BY Account__c
        ]) {
            counts.put((Id) ar.get('accountId'), (Integer) ar.get('total'));
        }

        List<Account> toUpdate = new List<Account>();
        for (Id accountId : counts.keySet()) {
            toUpdate.add(new Account(Id = accountId, Active_Placements__c = counts.get(accountId)));
        }
        update toUpdate;
    }

    private static void collectAccountIds(List<Placement__c> records, Set<Id> accountIds) {
        if (records == null) {
            return;
        }
        for (Placement__c p : records) {
            if (p.Account__c != null) {
                accountIds.add(p.Account__c);
            }
        }
    }
}

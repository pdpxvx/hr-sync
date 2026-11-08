@IsTest
private class PlacementTriggerHandlerTest {

    @IsTest
    static void countsOnlyActivePlacementsAndReactsToChanges() {
        Account acc = new Account(Name = 'Test SL', ERP_Id__c = 'CL-TEST');
        insert acc;
        Candidate__c cand = new Candidate__c(Name = 'Anna Puig', ERP_Id__c = 'CA-TEST');
        insert cand;

        List<Placement__c> placements = new List<Placement__c>{
            new Placement__c(ERP_Id__c = 'PL-T1', Account__c = acc.Id, Candidate__c = cand.Id, Status__c = 'Active'),
            new Placement__c(ERP_Id__c = 'PL-T2', Account__c = acc.Id, Candidate__c = cand.Id, Status__c = 'Active'),
            new Placement__c(ERP_Id__c = 'PL-T3', Account__c = acc.Id, Candidate__c = cand.Id, Status__c = 'Closed')
        };

        Test.startTest();
        insert placements;
        Assert.areEqual(2, activeCount(acc.Id), 'Only Active placements are counted');

        placements[0].Status__c = 'Closed';
        update placements[0];
        Assert.areEqual(1, activeCount(acc.Id), 'Closing a placement decreases the count');

        delete placements[1];
        Assert.areEqual(0, activeCount(acc.Id), 'Deleting a placement decreases the count');
        Test.stopTest();
    }

    private static Integer activeCount(Id accountId) {
        return [SELECT Active_Placements__c FROM Account WHERE Id = :accountId].Active_Placements__c.intValue();
    }
}
